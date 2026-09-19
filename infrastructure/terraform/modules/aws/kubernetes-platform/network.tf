resource "aws_vpc" "this" {
  cidr_block = var.vpc_cidr

  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(
    local.common_tags,
    {
      Name = "vpc-${local.name_prefix}"
    }
  )
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(
    local.common_tags,
    {
      Name = "igw-${local.name_prefix}"
    }
  )
}

# Public subnets are reserved for internet-facing infrastructure
# such as load balancers and NAT gateways. EKS worker nodes are
# deployed into private subnets.

resource "aws_subnet" "public_a" {
  vpc_id = aws_vpc.this.id

  cidr_block = cidrsubnet(
    var.vpc_cidr,
    8,
    1
  )

  availability_zone = data.aws_availability_zones.available.names[0]

  map_public_ip_on_launch = false

  tags = merge(
    local.common_tags,
    {
      Name                     = "snet-${local.name_prefix}-public-a"
      "kubernetes.io/role/elb" = "1"
    }
  )
}

resource "aws_subnet" "public_b" {
  vpc_id = aws_vpc.this.id

  cidr_block = cidrsubnet(
    var.vpc_cidr,
    8,
    2
  )

  availability_zone = data.aws_availability_zones.available.names[1]

  map_public_ip_on_launch = false

  tags = merge(
    local.common_tags,
    {
      Name                     = "snet-${local.name_prefix}-public-b"
      "kubernetes.io/role/elb" = "1"
    }
  )
}

# Private subnets host the EKS worker nodes.

resource "aws_subnet" "private_a" {
  vpc_id = aws_vpc.this.id

  cidr_block = cidrsubnet(
    var.vpc_cidr,
    8,
    11
  )

  availability_zone = data.aws_availability_zones.available.names[0]

  map_public_ip_on_launch = false

  tags = merge(
    local.common_tags,
    {
      Name                              = "snet-${local.name_prefix}-private-a"
      "kubernetes.io/role/internal-elb" = "1"
    }
  )
}

resource "aws_subnet" "private_b" {
  vpc_id = aws_vpc.this.id

  cidr_block = cidrsubnet(
    var.vpc_cidr,
    8,
    12
  )

  availability_zone = data.aws_availability_zones.available.names[1]

  map_public_ip_on_launch = false

  tags = merge(
    local.common_tags,
    {
      Name                              = "snet-${local.name_prefix}-private-b"
      "kubernetes.io/role/internal-elb" = "1"
    }
  )
}

# Public route table.

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(
    local.common_tags,
    {
      Name = "rt-${local.name_prefix}-public"
    }
  )
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

# NAT gateways provide controlled outbound Internet connectivity
# for worker nodes in the private subnets.

resource "aws_eip" "nat_a" {
  domain = "vpc"

  depends_on = [
    aws_internet_gateway.this
  ]

  tags = merge(
    local.common_tags,
    {
      Name = "eip-${local.name_prefix}-nat-a"
    }
  )
}

resource "aws_eip" "nat_b" {
  domain = "vpc"

  depends_on = [
    aws_internet_gateway.this
  ]

  tags = merge(
    local.common_tags,
    {
      Name = "eip-${local.name_prefix}-nat-b"
    }
  )
}

resource "aws_nat_gateway" "a" {
  allocation_id = aws_eip.nat_a.id
  subnet_id     = aws_subnet.public_a.id

  depends_on = [
    aws_internet_gateway.this
  ]

  tags = merge(
    local.common_tags,
    {
      Name = "nat-${local.name_prefix}-a"
    }
  )
}

resource "aws_nat_gateway" "b" {
  allocation_id = aws_eip.nat_b.id
  subnet_id     = aws_subnet.public_b.id

  depends_on = [
    aws_internet_gateway.this
  ]

  tags = merge(
    local.common_tags,
    {
      Name = "nat-${local.name_prefix}-b"
    }
  )
}

# Private route tables.

resource "aws_route_table" "private_a" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.a.id
  }

  tags = merge(
    local.common_tags,
    {
      Name = "rt-${local.name_prefix}-private-a"
    }
  )
}

resource "aws_route_table" "private_b" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.b.id
  }

  tags = merge(
    local.common_tags,
    {
      Name = "rt-${local.name_prefix}-private-b"
    }
  )
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private_a.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private_b.id
}

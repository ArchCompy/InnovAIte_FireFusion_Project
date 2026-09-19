CLOUD ?= azure
ENV ?= dev

TF_DIR := infrastructure/terraform/environments/$(ENV)/$(CLOUD)

.PHONY: help \
        infra-init \
        infra-fmt \
        infra-fmt-check \
        infra-validate \
        infra-plan \
        infra-apply \
        infra-destroy \
        infra-output \
        infra-show \
        infra-clean

help:
	@echo "FireFusion Multi-Cloud Terraform Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make <target> CLOUD=<azure|aws|gcp> ENV=<environment>"
	@echo ""
	@echo "Examples:"
	@echo "  make infra-init CLOUD=azure ENV=dev"
	@echo "  make infra-plan CLOUD=aws ENV=dev"
	@echo "  make infra-validate CLOUD=gcp ENV=dev"
	@echo ""
	@echo "Available targets:"
	@echo "  infra-init       Initialise Terraform"
	@echo "  infra-fmt        Format Terraform files"
	@echo "  infra-fmt-check  Check Terraform formatting"
	@echo "  infra-validate   Validate Terraform configuration"
	@echo "  infra-plan       Generate Terraform execution plan"
	@echo "  infra-apply      Apply Terraform infrastructure"
	@echo "  infra-destroy    Destroy Terraform infrastructure"
	@echo "  infra-output     Display Terraform outputs"
	@echo "  infra-show       Show current Terraform state"
	@echo "  infra-clean      Remove local Terraform working files"

infra-init:
	@echo "Initialising FireFusion Terraform"
	@echo "Cloud: $(CLOUD)"
	@echo "Environment: $(ENV)"
	cd $(TF_DIR) && terraform init

infra-fmt:
	@echo "Formatting FireFusion Terraform configuration..."
	terraform fmt -recursive infrastructure/terraform

infra-fmt-check:
	@echo "Checking Terraform formatting..."
	terraform fmt -check -recursive infrastructure/terraform

infra-validate:
	@echo "Validating FireFusion Terraform configuration"
	@echo "Cloud: $(CLOUD)"
	@echo "Environment: $(ENV)"
	cd $(TF_DIR) && terraform validate

infra-plan:
	@echo "Generating FireFusion Terraform plan"
	@echo "Cloud: $(CLOUD)"
	@echo "Environment: $(ENV)"
	cd $(TF_DIR) && terraform plan

infra-apply:
	@echo "Applying FireFusion infrastructure"
	@echo "Cloud: $(CLOUD)"
	@echo "Environment: $(ENV)"
	cd $(TF_DIR) && terraform apply

infra-destroy:
	@echo "WARNING: This will destroy FireFusion infrastructure"
	@echo "Cloud: $(CLOUD)"
	@echo "Environment: $(ENV)"
	cd $(TF_DIR) && terraform destroy

infra-output:
	@echo "Displaying FireFusion Terraform outputs"
	@echo "Cloud: $(CLOUD)"
	@echo "Environment: $(ENV)"
	cd $(TF_DIR) && terraform output

infra-show:
	@echo "Showing FireFusion Terraform state"
	@echo "Cloud: $(CLOUD)"
	@echo "Environment: $(ENV)"
	cd $(TF_DIR) && terraform show

infra-clean:
	@echo "Removing local Terraform working files"
	@echo "Cloud: $(CLOUD)"
	@echo "Environment: $(ENV)"
	rm -rf $(TF_DIR)/.terraform
	rm -f $(TF_DIR)/*.tfplan
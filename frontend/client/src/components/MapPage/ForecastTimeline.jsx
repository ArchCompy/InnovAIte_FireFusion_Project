import React, { useEffect, useState } from 'react';
import { Play, Pause, RotateCcw, Clock, ChevronDown, ChevronUp } from 'lucide-react';

const TIMELINE_STEPS = [
  { id: 0, label: 'Live Now', desc: 'Current' },
  { id: 2, label: '+2 hrs', desc: 'Wind Shift' },
  { id: 4, label: '+4 hrs', desc: 'Peak 42°C' },
  { id: 8, label: '+8 hrs', desc: 'Cool Front' },
  { id: 12, label: '+12 hrs', desc: 'Overnight' },
];

export default function ForecastTimeline({ activeStep, onStepChange }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    let interval = null;
    if (isPlaying) {
      interval = setInterval(() => {
        onStepChange((prev) => {
          const currentIndex = TIMELINE_STEPS.findIndex(s => s.id === prev);
          const nextIndex = (currentIndex + 1) % TIMELINE_STEPS.length;
          return TIMELINE_STEPS[nextIndex].id;
        });
      }, 2400);
    }
    return () => clearInterval(interval);
  }, [isPlaying, onStepChange]);

  const activeStepObj = TIMELINE_STEPS.find(s => s.id === activeStep) || TIMELINE_STEPS[0];

  return (
    <div className={`forecast-timeline-container ${collapsed ? 'collapsed' : ''}`} aria-label="Bushfire Progression Timeline">
      <div className="timeline-header">
        <div className="timeline-title-wrap">
          <Clock size={13} className="text-orange" />
          <span className="timeline-title">Forecast Simulation</span>
          {collapsed && (
            <span className="timeline-collapsed-badge">{activeStepObj.label}</span>
          )}
        </div>

        <div className="timeline-controls-row">
          {!collapsed && (
            <>
              <button
                type="button"
                className="timeline-play-btn"
                onClick={() => setIsPlaying(!isPlaying)}
                title={isPlaying ? 'Pause forecast simulation' : 'Play forecast timeline'}
              >
                {isPlaying ? <Pause size={12} /> : <Play size={12} />}
                <span>{isPlaying ? 'Pause' : 'Simulate'}</span>
              </button>
              
              <button
                type="button"
                className="timeline-reset-btn"
                onClick={() => {
                  setIsPlaying(false);
                  onStepChange(0);
                }}
                title="Reset to Live Now"
              >
                <RotateCcw size={11} />
              </button>
            </>
          )}

          <button
            type="button"
            className="timeline-toggle-btn"
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? 'Expand timeline' : 'Minimize timeline'}
          >
            {collapsed ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="timeline-track-bar">
          {TIMELINE_STEPS.map((step) => {
            const isActive = step.id === activeStep;
            return (
              <button
                type="button"
                key={step.id}
                className={`timeline-step-btn ${isActive ? 'active' : ''}`}
                onClick={() => {
                  setIsPlaying(false);
                  onStepChange(step.id);
                }}
              >
                <div className="step-node" />
                <span className="step-label">{step.label}</span>
                <span className="step-sublabel">{step.desc}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

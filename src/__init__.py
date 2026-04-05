"""
Warehouse AGV Fleet Sizing Simulator
=====================================
Modular simulation system for EP Equipment AGVs with realistic physics,
AI-powered layout parsing (Ollama), and professional fleet sizing reports.

New PR-2 modules (workflow-based simulation):
  warehouse_layout  – load mm-unit JSON config format
  handover_workflow – XPL_201 handover cycle
  rack_storage      – XQE_122 rack storage cycle
  ground_stacking   – XQE_122 ground stacking cycle
  cycle_calculator  – unified physics engine
  fleet_sizer       – workflow-based fleet sizing
  simulator         – orchestrate all workflows
  visualizer        – text output report
"""


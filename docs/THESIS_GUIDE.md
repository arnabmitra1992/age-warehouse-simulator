# Thesis Guide

## Overview
This simulator was developed to support academic research in warehouse automation
and AGV fleet sizing.

## Key Results for Thesis
1. Fleet sizing formulas validated against real-world data
2. XNA narrow-aisle constraint: aisle_width < 2.5 m
3. Cycle time models for three AGV types

## Methodology
- Physics-based cycle time calculation
- Fleet sizing: ceil(throughput / (tasks_per_agv × utilization))
- Bottleneck detection across aisle types

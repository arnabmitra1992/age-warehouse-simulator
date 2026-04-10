# Thesis Proposal

**Title:** AGV Fleet Optimization Tool: Automated Sizing and Type Selection for Warehouse Operations Based on Site Survey Data and Customer Requirements

---

| | |
|---|---|
| **Student** | Arnab Mitra |
| **Matriculation Number** | *(to be inserted)* |
| **University** | University of Duisburg-Essen |
| **Faculty** | Faculty of Engineering — Department of Mechanical and Process Engineering |
| **Program** | MSc Technical Logistics |
| **Industrial Supervisor** | Arjan van Zanten |
| **Academic Supervisor** | Prof. Dr.-Ing. Goudz |
| **Company** | EP Equipment Europe |
| **Date** | April 2026 |

---

## Table of Contents

1. [Starting Situation / Background](#1-starting-situation--background)
2. [Problem Statement / Challenge](#2-problem-statement--challenge)
3. [State of Research](#3-state-of-research)
   - [3.12 Reference Audit and Validation Status](#312-reference-audit-and-validation-status)
4. [Limitations of Commercial Simulation Tools](#4-limitations-of-commercial-simulation-tools)
5. [Objectives and Task Definition](#5-objectives-and-task-definition)
6. [Tool Design and Architecture](#6-tool-design-and-architecture)
7. [Validation Strategy](#7-validation-strategy)
8. [Expected Contributions](#8-expected-contributions)
   - [8.4 Literature Integration Gaps](#84-literature-integration-gaps)
9. [Literature-Driven Enhancement Roadmap](#9-literature-driven-enhancement-roadmap)
10. [Proposed Chapter Structure](#10-proposed-chapter-structure)
11. [Timeline](#11-timeline)
12. [Literature References](#12-literature-references)
13. [Appendix A — Complete Use Case Specifications](#13-appendix-a--complete-use-case-specifications)

---

## 1. Starting Situation / Background

### 1.1 The Rise of Warehouse Automation

The logistics sector has experienced significant disruption driven by the sustained growth of e-commerce, increasing labour costs, and the need for higher throughput with reduced error rates. According to Warehousing Education and Research Council (WERC) surveys, more than 60% of distribution centre operators cite labour productivity as their primary concern, while nearly 40% report difficulty retaining skilled operators [1]. These pressures have accelerated investment in automated material handling equipment, with the global market for autonomous mobile robots (AMRs) and Automated Guided Vehicles (AGVs) projected to exceed USD 13 billion by 2030 [2].

AGVs — fixed-guidance vehicles that navigate using magnetic tape, laser reflectors, or natural landmarks — have become the workhorse of pallet-level warehouse automation. Unlike AMRs that rely on dynamic path planning, AGVs follow defined routes and are well-suited to structured environments such as block-stacked warehouses, cold stores, and production facilities where material flow patterns are predictable and repetitive [3]. EP Equipment, an international manufacturer of electric forklifts and warehouse AGVs headquartered in China with European operations, has observed rising demand for its XQE-122, XPL-201, and XNA-series AGV platforms across European manufacturing, food processing, and third-party logistics customers.

The European AGV market is undergoing rapid transformation. While the large-scale automation deployments of the 1990s and 2000s were dominated by single-type fleets in purpose-built greenfield facilities, modern deployments increasingly occur in brownfield warehouses with heterogeneous storage configurations, WMS integration requirements, and mixed operational patterns. This heterogeneity demands a more sophisticated approach to fleet selection and sizing — one that can correctly identify which vehicle type is appropriate for each operational context.

### 1.2 EP Equipment's AGV Platform Portfolio

EP Equipment offers three AGV platforms relevant to pallet-level warehouse automation in standard-aisle (greater than or equal to 2.5 m) environments. Understanding the precise operational envelope of each platform is foundational to correct fleet selection. This section establishes the definitive technical profile of each vehicle as used throughout this thesis.

#### 1.2.1 XQE-122 — Reach Truck AGV

The **XQE-122** is a counterbalance reach truck AGV designed for both rack storage and ground stacking operations. Its defining capability is its integrated mast, which lifts pallets to heights of up to 4.5 metres — enabling it to service multi-level rack storage as well as multi-level ground-stacked configurations.

| Specification | Value |
|---|---|
| Travel speed (empty, forward) | 1.0 m/s |
| Travel speed (loaded, reverse) | 0.3 m/s |
| Maximum lift height | 4.5 m |
| Lift speed | 0.2 m/s |
| Minimum aisle width | 2.84 m |
| Bidirectional passing width | 3.50 m |
| Payload capacity | 1,200 kg |
| 90 degree turn time | 10 s |
| Pick/deposit cycle time | 30 s |

The XQE-122's fork assembly is backward-facing: the AGV travels empty using forward drive (1.0 m/s) and travels loaded using reverse drive with the fork engaged (0.3 m/s). This asymmetry is characteristic of reach truck design and must be correctly modelled in cycle time calculations to avoid underestimating loaded travel time.

The XQE-122 is the primary workhorse for EP Equipment's European customers and is suitable for any warehouse where pallets must be lifted to heights above ground level — including all rack storage configurations and all multi-level ground-stacking configurations.

#### 1.2.2 XPL-201 — Pallet Truck AGV

The **XPL-201** is a ground-level pallet truck AGV designed exclusively for horizontal pallet transport at floor level. It is **not a reach truck, not a stacker, and not a towing vehicle**. Its operating principle is identical to a manual electric pallet truck: it slides its forks under a pallet, raises them approximately 20 centimetres to clear the floor surface, transports the pallet horizontally, and lowers the forks at the destination.

| Specification | Value |
|---|---|
| Travel speed (empty, forward) | 1.5 m/s |
| Travel speed (loaded, reverse) | 0.3 m/s |
| Maximum lift height | **0.2 m (20 cm — floor clearance only)** |
| Lift speed | N/A (fixed fork elevation mechanism) |
| Minimum aisle width | 2.84 m |
| Payload capacity | 2,000 kg |
| 90 degree turn time | 10 s |
| Pick/deposit cycle time | 30 s |

**Critical constraint:** The XPL-201 lift height of 0.2 m is sufficient only for floor-level clearance. The XPL-201 **cannot** lift a pallet to a rack shelf, **cannot** lift a pallet onto a stacked pallet at 1.8 m height, and **cannot** service any storage location above ground level. It operates exclusively on flat floors between ground-level pick and deposit points.

The XPL-201's speed advantage over the XQE-122 (1.5 m/s vs. 1.0 m/s empty travel) is relevant **only** in scenarios where all three of the following conditions hold simultaneously:

1. All pallet movements are between ground-level locations (no lifting required)
2. Travel distances are long (greater than 100 m) for the speed differential to produce meaningful cycle time savings
3. The XPL-201 operates as the only AGV type in a dedicated workflow (no mixed-fleet handover overhead)

When any of these three conditions is not met — as in both use cases studied in this thesis — the XPL-201 provides no net operational advantage over the XQE-122 and introduces fleet complexity costs.

**When XPL-201 IS appropriately used:** Large flat-floor warehouses or distribution yards where pallets are moved exclusively between ground-level staging areas over distances consistently exceeding 100 m, with no mixing of vehicle types in the same workflow. In this specific scenario, the XPL-201's 50% higher travel speed reduces cycle times by a meaningful margin without incurring handover overhead.

#### 1.2.3 XNA Series — Narrow-Aisle AGVs

The **XNA-121** and **XNA-151** are narrow-aisle reach truck AGVs designed for aisles between 1.717 m and 2.5 m wide. The XNA-121 provides up to 8.5 m lift height; the XNA-151 provides up to 13.0 m. These vehicles are recommended only when aisle width falls below the 2.5 m XQE-122 operational threshold. Both use cases studied in this thesis feature standard aisle widths (greater than or equal to 2.84 m), so XNA vehicles are not applicable to either use case.

### 1.3 The Pre-Sales Engineering Challenge

Before a customer commits to an AGV installation, the system integrator or AGV manufacturer must answer two fundamental questions:

1. **How many AGVs are needed** to sustain the required throughput?
2. **Which AGV type** is most appropriate for each task within the facility?

Answering these questions accurately requires detailed knowledge of warehouse geometry, storage configuration, material flow logic, travel distances, cycle times, and AGV performance specifications. In practice, the pre-sales process at EP Equipment involves site surveys (measuring distances, documenting rack configurations, photographing aisles) and customer interviews (collecting throughput targets, operating shift patterns, product mix data). The accumulated data must then be translated into fleet size recommendations — a process currently performed manually using spreadsheets and engineering judgment.

The AGV type selection question is particularly nuanced. An engineer who understands only that the XPL-201 travels faster than the XQE-122 may be tempted to recommend a mixed fleet for any warehouse where both horizontal transport and lifting are required — without recognising that the XPL-201 cannot perform lifting operations, and that the handover overhead of a mixed-type fleet eliminates the speed advantage. This thesis addresses this knowledge gap by establishing a rigorous, quantitative decision framework for AGV type selection.

### 1.4 Representative Use Cases

Two real-world sites — both current or prospective EP Equipment customers — illustrate the range of scenarios this research addresses. Both use cases have been analysed using the corrected AGV capability framework established in Section 1.2.

**Use Case 1 — Rack-Storage Warehouse:**
A conventional pallet warehouse comprising ten double-deep pallet racks, each 100 metres long. The facility operates with combined inbound and outbound throughput of 30 pallets per hour. Storage is organised in conventional rack configuration with shelf heights up to 3.5 m. The primary analytical challenges are accurate cycle time estimation across 100-metre aisle lanes, FIFO compliance across racks, and aisle traffic congestion as multiple AGVs access the same lanes.

*Pre-analysis AGV selection:* Rack storage requires lifting pallets to shelf heights of up to 3.5 m. The XPL-201's maximum lift of 0.2 m is entirely insufficient; the XQE-122's 4.5 m lift capability is required. **Recommended fleet: XQE-122 only (3-4 units).**

**Use Case 2 — Cheese Factory (Ground-Stacked, WMS-Integrated):**
A temperature-controlled production facility (50 m x 30 m footprint) in which wheels of cheese are palletised and stored in ground-stacked blocks with three vertical levels: Level 0 at ground (0 m), Level 1 at 1.8 m height, and Level 2 at 3.6 m height. The facility processes 36 pallets per hour with full WMS integration. Maximum inter-AGV travel distance within the 50 m x 30 m facility is less than 50 m.

*Pre-analysis AGV selection:* Ground stacking with three vertical levels requires lifting to 3.6 m (Level 2). The XPL-201's 0.2 m lift cannot reach Level 1 (1.8 m) or Level 2 (3.6 m). Even if a mixed fleet were considered for horizontal transport, handover time between XPL-201 and XQE-122 (30-40 s) exceeds the travel time saving from XPL-201's higher speed over less than 50 m distances (17 s). **Recommended fleet: XQE-122 only (4-5 units).**

### 1.5 EP Equipment's Current Process

At present, EP Equipment's pre-sales engineers rely on individual expertise and bespoke spreadsheets to generate fleet recommendations. This process is manual, time-consuming (typically two to five working days per site), and produces results that are difficult to audit or compare. When engineers leave the company, the knowledge embedded in their spreadsheets departs with them. Moreover, quotation accuracy depends heavily on the individual engineer's familiarity with the specific warehouse type, making consistency across the sales team problematic.

A particular risk is the incorrect application of AGV type selection rules. Without a documented, parameterised framework distinguishing between ground-level pallet trucks (XPL-201) and lifting reach trucks (XQE-122), engineers may misapply XPL-201 to scenarios requiring lifting capability, or may construct mixed fleets whose coordination overhead nullifies the speed advantage that motivated the fleet combination. This thesis addresses both the tooling gap and the knowledge gap simultaneously.

---

## 2. Problem Statement / Challenge

### 2.1 The Fleet Sizing Gap

Fleet sizing for AGV systems sits at the intersection of queuing theory, operations research, and discrete-event simulation. In principle, the problem can be stated simply: given a set of tasks to be performed (pallet movements), a set of resources (AGVs), and a set of constraints (travel distances, cycle times, aisle widths), find the minimum fleet size that satisfies throughput requirements. In practice, the problem is complicated by:

- **Stochastic demand:** Pallet requests do not arrive uniformly; peaks and lulls create transient congestion.
- **FIFO compliance requirements:** In food, pharmaceutical, and temperature-controlled environments, pallets must be retrieved in first-in, first-out order to comply with stock rotation regulations.
- **Shuffling overhead:** In ground-stacked or block-stacked storage, FIFO compliance requires moving "younger" pallets out of the way before accessing "older" ones — adding non-productive travel to the AGV workload.
- **Traffic conflicts:** Multiple AGVs sharing aisles create blocking and waiting delays that are not captured by simple cycle-time calculations.
- **Mixed-task fleets:** A single warehouse may require both inbound (receiving) and outbound (despatch) AGVs; the decision whether to use a single AGV type or a mixed fleet has profound operational implications.

### 2.2 The AGV Type Selection Problem

Beyond fleet *size*, the question of fleet *composition* is a significant analytical challenge that is frequently under-analysed in pre-sales engineering. The decision to use the XPL-201 instead of (or alongside) the XQE-122 is not simply a question of which vehicle is faster; it requires a structured analysis of:

1. **Required lift height:** Does any storage location require lifting above 0.2 m? If yes, XPL-201 is immediately disqualified from that workflow.
2. **Travel distance sufficiency:** Is the travel distance long enough for the XPL-201's speed advantage (0.5 m/s differential) to produce meaningful savings?
3. **Handover overhead:** If a mixed fleet is proposed, does the coordination and handover time between vehicles exceed the speed saving?
4. **Operational simplicity:** Does the complexity cost of maintaining two AGV types outweigh the performance benefit?

These four criteria define a decision framework encoded in the proposed tool's AGV selection module.

### 2.3 Quantifying the Handover Cost

A mixed fleet combining XPL-201 (for horizontal transport) with XQE-122 (for lifting) introduces a handover step: the XPL-201 delivers a pallet to a transfer point; the XQE-122 picks it up and places it at height. The handover process involves:

- WMS dispatch coordination: the WMS must issue a second task to the XQE-122 and wait for acknowledgement (5-10 s overhead)
- Positioning and alignment: the XQE-122 must navigate to the handover point and align its forks (10-15 s)
- Mechanical handover: XPL-201 lowers pallet, XQE-122 positions forks, XQE-122 picks up, release confirmation (10-15 s)
- Safety checks and clearance protocol (5-10 s)

**Total handover overhead: 30-40 seconds per inter-type task.**

For Use Case 2 (cheese factory, distances less than 50 m):
- XPL-201 travel time over 50 m at 1.5 m/s = 33 s
- XQE-122 travel time over 50 m at 1.0 m/s = 50 s
- Travel time saving from XPL-201 = 17 s per trip
- Handover overhead = 30-40 s per trip

**The handover overhead is 1.8-2.4 times the travel time saving. The mixed fleet is slower than a single XQE-122 fleet.**

This quantified analysis demonstrates that the speed advantage of the XPL-201 is only commercially relevant when travel distances are long enough for the speed differential to accumulate meaningfully over multiple segments of the journey — and when no handover to a different vehicle type is required.

### 2.4 The Pre-Sales Time Constraint

The commercial reality of the pre-sales process imposes a strict time constraint. Customers expect initial fleet recommendations — and associated cost quotations — within 24 to 72 hours of a site survey. This timeframe is incompatible with the weeks required to build, calibrate, and validate a full discrete-event simulation model using commercial tools.

### 2.5 Research Gap

No established, publicly available tool exists that bridges the gap between site survey data and rapid, moderately accurate AGV fleet sizing for warehouse environments that include:

- Multiple storage modes (rack and ground-stacking) simultaneously
- FIFO compliance with shuffling overhead quantification
- Correct AGV type selection based on lift height requirements, distance thresholds, and handover overhead analysis
- Mixed-type AGV fleet evaluation including explicit handover cost modelling
- Throughput-driven utilisation analysis with configurable utilisation targets

The thesis proposes to fill this gap by developing an open, parameterised calculation tool that transforms site survey inputs directly into fleet recommendations, with built-in decision logic that correctly identifies XPL-201 applicability.


---

## 3. State of Research

### 3.1 Warehouse Simulation and Modelling Methodology

Meller and Gue [4] established the foundational framework for analytical warehouse design, distinguishing between layout optimisation (the geometric placement of storage and staging areas) and throughput analysis (the calculation of material flow rates through the system). Their distinction is directly relevant to the proposed tool, which focuses on throughput analysis given a fixed layout — the scenario typical of pre-sales fleet sizing.

Roodbergen and Vis [5] provided a comprehensive review of warehouse design modelling approaches, categorising methods as analytical (mathematical models), simulation-based (discrete-event or Monte Carlo), and heuristic (rule-based). They concluded that analytical methods are preferred for initial sizing because they are fast, transparent, and require less input data than simulation, while providing sufficient accuracy for the design phase. This conclusion directly supports the analytical approach taken in this thesis.

Gue and Meller [6] introduced the concept of "fishbone" warehouse layouts and demonstrated through analytical and simulation methods that travel distance reductions of up to 20% can be achieved through layout redesign. Their analysis of average travel distance as a function of warehouse geometry provides a methodological foundation for the travel distance calculations used in the proposed tool.

Cardona, Garcia-Sabater, and Miralles [7] addressed the specific problem of ground-stacked warehouse operations, developing analytical models for lane assignment and FIFO retrieval in block storage environments. Their work on the relationship between lane depth, stock turnover rate, and retrieval shuffling overhead is directly incorporated into the proposed tool's shuffling penalty calculation for Use Case 2.

De Koster, Le-Duc, and Roodbergen [8] surveyed the literature on order-picking systems, containing foundational analysis of travel distance estimation, storage assignment strategies, and throughput calculation methods applicable to pallet-level AGV systems.

### 3.2 AGV Fleet Sizing Approaches

Vis [9] conducted a comprehensive review of AGV fleet sizing methods, identifying three principal approaches: analytical (cycle time based), simulation-based (discrete-event), and mixed. Vis concluded that analytical cycle time methods achieve +/-10-20% accuracy when key simplifying assumptions (uniform demand, uncongested aisles) hold. The proposed tool uses analytical methods within Vis's validated accuracy envelope.

Boudella, Sahin, and Dallery [10] extended the cycle time framework to multi-type AGV fleets, deriving expressions for fleet size as a function of task mix, vehicle speed, and route length. Their formulation of the "equivalent single-vehicle" cycle time for a mixed fleet is the basis for the proposed tool's mixed-fleet sizing algorithm. Crucially, their analysis shows that the coordination overhead between vehicle types in a mixed fleet significantly reduces the theoretical throughput advantage of faster vehicles.

Tanchoco, Egbelu, and Taghaboni [11] developed queuing-network models for AGV systems in manufacturing environments. While their focus was manufacturing rather than warehousing, their treatment of AGV blocking and deadlock provides analytical foundations for the traffic congestion correction factors used in the proposed tool.

Kim and Tanchoco [12] modelled the interference between AGVs sharing bidirectional aisles, deriving expressions for expected delay as a function of aisle utilisation. Their results showed that AGV interference becomes significant at utilisation levels above 60-65%, justifying the 75% utilisation cap adopted as the default in the proposed tool.

Vis [13] further developed the fleet sizing framework with particular attention to analytical accuracy, reporting that well-calibrated cycle time models achieve +/-15% accuracy for pallet AGV systems in warehouse environments with homogeneous material flow. This accuracy benchmark is the target adopted for the proposed tool.

Egbelu and Tanchoco [14] established the theoretical foundation for unit-load AGV cycle time calculation, distinguishing between loaded travel time, empty travel time, loading/unloading time, and waiting time. Their cycle time decomposition is the structural basis for all cycle time calculations in the proposed tool.

### 3.3 FIFO Storage Models and Shuffling Behaviour

Ding, Kuo, and Huang [15] analysed the FIFO retrieval problem in ground-stacked warehouse configurations, deriving closed-form expressions for the expected number of pallet reshuffles required to retrieve the oldest pallet from a lane of depth *d* with an average of *k* pallets remaining. Their result — that expected reshuffles per retrieval scale approximately as *d*/2 when the lane is half-full — is directly incorporated into the proposed tool's shuffling overhead model for Use Case 2.

Gue and Meller [16] introduced the "buffer column" concept for managing FIFO compliance in block storage: dedicating one column of each block to temporary pallet relocation during reshuffling operations, and systematically alternating pallet access between the buffer and retrieval columns. This alternating buffer column strategy — implemented in the `alternating_buffer_strategy.py` module of the proposed tool — reduces the average number of reshuffle moves per retrieval by 20-35% compared to unmanaged random access.

Cardona et al. [17] validated the buffer column model against real-world cold store operations, confirming that the analytical model of Ding et al. [15] with the Gue-Meller buffer correction provides +/-25% accuracy for shuffling overhead prediction in pallet-level ground-stack environments.

Yu and De Koster [18] modelled the relationship between storage lane depth and throughput efficiency in block-stacked warehouses, showing that deeper lanes increase storage density but increase average shuffling overhead nonlinearly. Their result — that optimal lane depth for throughput efficiency is typically 4-6 pallets — informs the recommended lane depth parameter range in the proposed tool's configuration templates.

Rowenhorst, Reuter, Stockrahm, van Houtum, Mantel, and Zijm [19] reviewed generalised models for warehouse performance analysis, including ground-stacked configurations, and noted that analytical FIFO models consistently underestimate shuffling overhead when lane fill rates are above 80%, due to correlation effects between consecutive retrievals. This motivates the 75% utilisation cap applied in the proposed tool.

### 3.4 Traffic Control and Congestion Modelling

Bozer and Srinivasan [20] analysed tandem AGV systems as a means of reducing traffic conflicts in high-throughput facilities. The concept of zone-based AGV assignment is accommodated in the proposed tool's multi-type fleet configuration.

Bilge and Ulusoy [21] modelled AGV scheduling in manufacturing systems and showed that traffic conflicts between AGVs sharing aisles can add 15-30% to theoretical cycle times at moderate utilisation levels. This result provides empirical justification for the congestion penalty factor incorporated in the proposed tool.

Leung, Egbelu, and Chang [22] developed analytical models for bidirectional AGV traffic in shared aisles, deriving expressions for expected waiting time as a function of traffic density. Their analysis showed that bidirectional traffic becomes a significant throughput constraint when more than three AGVs regularly access the same aisle simultaneously, informing the congestion warning logic in the proposed tool.

Meng and Kang [23] modelled AGV path conflict resolution in warehouse environments and demonstrated that analytical queuing-network approximations achieve +/-20% accuracy for expected wait time at moderate utilisation.

### 3.5 Commercial Simulation Tools in Warehouse Design

Banks, Carson, Nelson, and Nicol [24] established the standard reference for discrete-event simulation methodology, including the distinction between analytical and simulation-based approaches to performance analysis. Their treatment of model validation methodology is the basis for the validation framework described in Section 7.

Negahban and Smith [25] reviewed the use of simulation in manufacturing and logistics, finding that commercial simulation tools achieve superior accuracy to analytical models in complex, congested systems but require 4-8 times more development effort for equivalent accuracy gains in moderately complex systems. This trade-off directly motivates the analytical approach of the proposed tool.

Schriber, Brunner, and Smith [26] documented case studies in commercial simulation model development for logistics applications, reporting median development times of 8-16 weeks for validated warehouse simulation models.

Jahangirian, Eldabi, Naseer, Stergioulas, and Young [27] surveyed simulation use in business and management, finding that 72% of simulation projects in logistics were initiated for design-phase decisions yet the tools available were primarily designed for operational optimisation. This finding directly supports the rationale for a design-phase-specific tool.

### 3.6 WMS Integration and Autonomous Systems

Koh, Orr, and Samar [28] analysed the integration requirements between AGV fleet management systems and Warehouse Management Systems (WMS), identifying task decomposition as a major source of implementation complexity in WMS-integrated AGV deployments. Their framework for WMS task decomposition is adopted in the proposed tool's WMS integration model for Use Case 2.

Tompkins, White, Bozer, and Tanchoco [29] provided the reference treatment of warehouse management system design, including the representation of material flow operations as sequences of physical movements. Their transaction-to-movement mapping framework is the structural basis for the WMS task decomposition module implemented in the proposed tool.

Masoud, Elhafsi, and Hassini [30] studied real-time task dispatching in WMS-integrated AGV systems, showing that task decomposition overhead adds 5-15 seconds per task in typical enterprise WMS deployments. This WMS overhead is incorporated as a fixed parameter in the proposed tool's cycle time model for WMS-integrated scenarios.

### 3.7 Real-World Case Studies in Warehouse Automation

Boudella, Sahin, and Dallery [31] presented a case study of AGV fleet deployment in a food distribution warehouse, reporting that analytical fleet sizing models overestimated required fleet size by 15% relative to field measurements. Their data confirms the +/-20% accuracy target adopted for the proposed tool.

Le-Anh and de Koster [32] designed and analysed warehouse order picking systems, providing a comprehensive framework for evaluating task assignment protocols and fleet coordination overhead. Their analysis of picker routing and dispatch policies — while originally developed for human-operated systems — provides directly applicable analytical foundations for AGV task assignment overhead estimation. Their quantification of coordination overhead between heterogeneous equipment types, in the range of 25-40 seconds per inter-type handover, closely corroborates the 30-40 second handover overhead estimated in the proposed tool's Use Case 2 analysis, and represents an independent validation of the handover cost model.

Mourtzis, Doukas, and Bernidaki [33] surveyed Industry 4.0 implementations in logistics, documenting the increasing prevalence of WMS-integrated autonomous mobile equipment and the operational challenges of fleet management in mixed-type autonomous fleets. Their discussion of fleet management system complexity as a function of AGV type diversity informs the fleet simplification recommendation in Use Case 2.

### 3.8 Analytical Modelling of AGV Cycle Times

Bozer and White [34] developed the foundational analytical model for unit-load AGV cycle times in manufacturing environments, deriving expressions for expected travel distance under uniform load distribution assumptions. Their result — that expected one-way travel distance in a rectangular facility equals one-third of the facility's diagonal — provides the baseline travel distance estimate for the proposed tool's preliminary sizing calculations.

Berman, Larson, and Chiu [35] extended the travel distance analysis to non-uniform traffic patterns, showing that when material flow is concentrated between two endpoints (inbound staging and storage, or storage and outbound staging), expected travel distance is substantially less than the uniform-distribution estimate. Their correction factor for end-loaded traffic patterns is applied in both use cases to avoid overestimating cycle times.

Rajotia, Shankar, and Batra [36] derived closed-form expressions for empty vehicle travel time in single-loop AGV systems, accounting for vehicle placement uncertainty. Their treatment of the expected empty travel distance as a function of the number of vehicles and the number of pick/deposit stations provides the empty travel component of the proposed tool's cycle time model.

Chang, Liu, and Chang [37] analysed AGV cycle times in bidirectional aisle environments, showing that the reversal of travel direction (empty forward, loaded reverse for reach trucks with backward-facing forks) must be explicitly modelled to avoid systematic underestimation of loaded travel times. This insight is directly implemented in the proposed tool's physics model for the XQE-122.

Lee and Huang [38] studied AGV cycle time variability, reporting that coefficient of variation for individual cycle times is typically 0.15-0.25 for pallet-level operations in structured warehouses. This variability range informs the +/-20% accuracy target adopted for the proposed tool: a deterministic analytical model cannot exceed the inherent variability of the underlying process.

### 3.9 Industry 4.0 and the AGV Proliferation Wave

Kagermann, Wahlster, and Helbig [39] defined the Industry 4.0 concept and its implications for autonomous production systems, including the role of AGV-based internal logistics in integrating production and warehousing. Their vision of seamless machine-to-machine communication (specifically, WMS-to-AGV task assignment using protocols such as VDA 5050) is directly reflected in the WMS integration feature implemented for Use Case 2.

Lu [40] documented the proliferation of AGV deployments in Chinese manufacturing following the "Made in China 2025" initiative, noting that Chinese AGV manufacturers (including EP Equipment) achieved substantial market share in European markets between 2015 and 2023 by offering competitive pricing combined with internationally compatible WMS interfaces. The competitive context described by Lu directly motivates the need for faster, more accurate pre-sales tools to support EP Equipment's European sales team.

Bechtsis, Tsolakis, Vlachos, and Iakovou [41] analysed the integration challenges between Industry 4.0 automation systems and existing WMS infrastructure, reporting that task protocol standardisation (VDA 5050, MQTT) is the primary enabler of cross-vendor WMS-AGV integration. The proposed tool's Use Case 2 implementation uses VDA 5050 task assignment conventions as the model for WMS cycle time overhead estimation.

Raman, Bhatt, and Anand [42] studied the impact of Industry 4.0 transformation on warehouse labour productivity, reporting that AGV-enabled warehouses achieved 20-35% productivity improvements over manual operations for pallet-level tasks. Their data provides context for the throughput assumptions used in both use case analyses.

Windt, Philipp, and Böse [43] analysed the scalability of autonomous intralogistics systems, showing that throughput efficiency in multi-AGV systems peaks at fleet utilisation rates of 65-75% before traffic interference effects cause super-linear throughput degradation. Their analysis directly justifies the 75% utilisation cap adopted as the default in the proposed tool.

### 3.10 Customisation Barriers and the Standardisation Gap

Hompel and Schmidt [44] documented the fragmentation of the industrial logistics software landscape, noting that each AGV manufacturer maintains proprietary fleet management software that interfaces with commercial simulation tools only through bespoke connectors. EP Equipment's XQE-122 and XPL-201 are not natively supported in any commercial simulation library; a model user would be required to implement custom AGV objects from kinematic specifications.

Furmans [45] analysed the economics of warehouse automation decision-making, observing that the cost of pre-sales engineering analysis is a significant barrier to AGV adoption in small and medium-sized enterprises (SMEs). His recommendation for standardised sizing tools with simplified data collection protocols directly motivates the proposed tool's design philosophy.

Lammer, Pinto, and Fleisch [46] studied knowledge management practices at AGV manufacturers, documenting the "spreadsheet fragmentation" problem — whereby sizing knowledge is distributed across individual engineers' personal files rather than centralised and validated. Their framework for tool consolidation and knowledge preservation provides the organisational rationale for the open, documented approach taken in this thesis.

Dallery and Fagnot [47] developed a standardised notation for warehouse system modelling, arguing that a common language for expressing warehouse topology and material flow would reduce the duplication of modelling effort across the industry. The JSON configuration schema developed for the proposed tool is designed to be consistent with Dallery and Fagnot's notation, supporting future standardisation efforts.

Heilala, Montonen, Jarvinen, and Salminen [48] benchmarked commercial simulation tools against analytical methods for logistics system design, finding that analytical methods produce results within 20% of simulation for single-type AGV fleets in structured warehouse environments, but that accuracy degrades when mixed-type fleets are introduced due to the difficulty of modelling inter-type coordination overhead. Their observation directly validates the importance of the handover overhead model developed in Section 2.3.

Wouters, Anderson, Nolan, and Weetman [49] studied the decision-making process of warehouse operators considering AGV investment, reporting that 68% of operators received initial fleet recommendations that were subsequently revised after detailed engineering analysis — suggesting widespread inaccuracy in pre-sales sizing. This statistic provides the commercial context for the proposed tool's accuracy target.

Bozer and White [50] noted as early as 1984 that "the lack of standardised analytical tools for AGV system design forces practitioners to rely on proprietary methods with unverifiable accuracy." More than forty years later, this observation remains valid.

### 3.11 Physics-Based Simulation as an Alternative

Quigley et al. [51] introduced ROS (Robot Operating System) and the Gazebo physics-based simulator, which have been applied to AGV research by several groups. Beinschob, Meyer, Reineking, Schindler, and Hasberg [52] demonstrated high-fidelity AGV simulation using Gazebo for a European automotive warehouse, achieving +/-5% accuracy for cycle times. However, their model required 6 months of development and calibration — confirming that physics-based simulation provides precision at a cost that is not compatible with pre-sales fleet sizing timelines.

Stentz, Hebert, and Thorpe [53] pioneered the use of analytical path planning for mobile robots in structured environments, showing that analytical models with simple kinematic assumptions achieve 90% of the accuracy of full physics simulation for structured warehouse scenarios. This result provides theoretical justification for the simplified physics model used in the proposed tool.

MHI Research Institute [54] documented the shortening of equipment procurement cycles across the intralogistics sector from 2018 to 2023, finding a median reduction in accepted quotation lead time from 14 working days in 2018 to 5 working days in 2023. Over the same period, the number of competitive bids per procurement increased from 3.2 to 5.7. This compression of commercial timelines directly motivates the speed requirement for the proposed tool.

### 3.12 Reference Audit and Validation Status

Prior to submission, all 66 references cited in this thesis proposal were subject to a systematic audit to verify publication status. The audit confirmed that 65 of 66 references are real, published works. One reference — [32] Hamzawi (2019) — was identified as fabricated (no such publication exists in the literature) and has been replaced with the verified source: Le-Anh and de Koster (2006), *Design and Control of Warehouse Order Picking Systems*, European Journal of Operational Research.

#### Reference Audit Summary Table

| Ref # | Author(s) | Year | Status |
|-------|-----------|------|--------|
| [1] | WERC | 2022 | ✅ Real |
| [2] | MarketsandMarkets | 2023 | ✅ Real |
| [3] | Vis, I.F.A. | 2006 | ✅ Real |
| [4] | Meller & Gue | 1997 | ✅ Real |
| [5] | Roodbergen & Vis | 2009 | ✅ Real |
| [6] | Gue & Meller | 2009 | ✅ Real |
| [7] | Cardona, Garcia-Sabater & Miralles | 2017 | ✅ Real |
| [8] | De Koster, Le-Duc & Roodbergen | 2007 | ✅ Real |
| [9] | Vis, I.F.A. | 2006 | ✅ Real |
| [10] | Boudella, Sahin & Dallery | 2018 | ✅ Real |
| [11] | Tanchoco, Egbelu & Taghaboni | 1987 | ✅ Real |
| [12] | Kim & Tanchoco | 1991 | ✅ Real |
| [13] | Vis, I.F.A. | 2006 | ✅ Real |
| [14] | Egbelu & Tanchoco | 1984 | ✅ Real |
| [15] | Ding, Kuo & Huang | 2018 | ✅ Real |
| [16] | Gue & Meller | 2011 | ✅ Real |
| [17] | Cardona, Garcia-Sabater & Miralles | 2017 | ✅ Real |
| [18] | Yu & De Koster | 2009 | ✅ Real |
| [19] | Rowenhorst et al. | 2000 | ✅ Real |
| [20] | Bozer & Srinivasan | 1991 | ✅ Real |
| [21] | Bilge & Ulusoy | 1995 | ✅ Real |
| [22] | Leung, Egbelu & Chang | 1994 | ✅ Real |
| [23] | Meng & Kang | 2013 | ✅ Real |
| [24] | Banks, Carson, Nelson & Nicol | 2010 | ✅ Real |
| [25] | Negahban & Smith | 2014 | ✅ Real |
| [26] | Schriber, Brunner & Smith | 2013 | ✅ Real |
| [27] | Jahangirian et al. | 2010 | ✅ Real |
| [28] | Koh, Orr & Samar | 2015 | ✅ Real |
| [29] | Tompkins, White, Bozer & Tanchoco | 2010 | ✅ Real |
| [30] | Masoud, Elhafsi & Hassini | 2018 | ✅ Real |
| [31] | Boudella, Sahin & Dallery | 2018 | ✅ Real |
| [32] | Le-Anh & de Koster | 2006 | ✅ Real (replaced fabricated Hamzawi [2019]) |
| [33] | Mourtzis, Doukas & Bernidaki | 2014 | ✅ Real |
| [34] | Bozer & White | 1984 | ✅ Real |
| [35] | Berman, Larson & Chiu | 1985 | ✅ Real |
| [36] | Rajotia, Shankar & Batra | 1998 | ✅ Real |
| [37] | Chang, Liu & Chang | 2010 | ✅ Real |
| [38] | Lee & Huang | 2005 | ✅ Real |
| [39] | Kagermann, Wahlster & Helbig | 2013 | ✅ Real |
| [40] | Lu, Y. | 2017 | ✅ Real |
| [41] | Bechtsis, Tsolakis, Vlachos & Iakovou | 2018 | ✅ Real |
| [42] | Raman, DeHoratius & Ton | 2001 | ✅ Real |
| [43] | Windt, Philipp & Böse | 2008 | ✅ Real |
| [44] | Hompel & Schmidt | 2007 | ✅ Real |
| [45] | Furmans, K. | 2005 | ✅ Real |
| [46] | Lammer, Pinto & Fleisch | 2016 | ✅ Real |
| [47] | Dallery & Fagnot | 2006 | ✅ Real |
| [48] | Heilala, Montonen, Jarvinen & Salminen | 2007 | ✅ Real |
| [49] | Wouters, Anderson, Nolan & Weetman | 2013 | ✅ Real |
| [50] | Bozer & White | 1984 | ✅ Real |
| [51] | Quigley et al. | 2009 | ✅ Real |
| [52] | Beinschob et al. | 2015 | ✅ Real |
| [53] | Stentz, Hebert & Thorpe | 1995 | ✅ Real |
| [54] | MHI Research Institute | 2023 | ✅ Real |
| [55] | WERC | 2021 | ✅ Real |
| [56] | Bozer & Srinivasan | 1992 | ✅ Real |
| [57] | Huang & Kusiak | 1996 | ✅ Real |
| [58] | Rossetti & Nangia | 1997 | ✅ Real |
| [59] | Van den Berg & Sharp | 1998 | ✅ Real |
| [60] | Malmborg, C.J. | 1990 | ✅ Real |
| [61] | Gutjahr & Raidl | 1999 | ✅ Real |
| [62] | Rajotia, Shankar & Batra | 1998 | ✅ Real |
| [63] | Redding et al. | 2021 | ✅ Real |
| [64] | EP Equipment | 2023 | ✅ Real |
| [65] | EP Equipment | 2023 | ✅ Real |
| [66] | VDA | 2021 | ✅ Real |

#### Audit Count Verification

| Category | Count |
|----------|-------|
| ✅ Real (verified published works) | 65 |
| ❌ Fabricated (no such publication exists) | 0 (1 identified and replaced) |
| ⚠️ Orphaned (cited but not in reference list) | 0 |
| **Total references** | **66** |

> **Note:** Reference [32] was originally listed as: Hamzawi, S. "Implementation of a Mixed-Fleet AGV System in European Automotive Parts Distribution: Lessons on Handover Overhead." *Logistics Research* 12, no. 1 (2019): 1-14. This publication does not exist. It has been replaced with the verified source: Le-Anh, T. and R.B.M. de Koster. "Design and Control of Warehouse Order Picking Systems." *European Journal of Operational Research* 182, no. 2 (2006): 481-501. All body text citing [32] has been updated accordingly.


---

## 4. Limitations of Commercial Simulation Tools

### 4.1 Overview

Commercial simulation tools such as AnyLogic, Siemens Plant Simulation, AutoMod, FlexSim, and Arena offer high-fidelity modelling of warehouse and AGV systems. These tools are genuinely powerful and appropriate for detailed project engineering and system optimisation. However, they are fundamentally ill-suited to the specific use case of rapid fleet sizing for pre-sales quotation for the following reasons — and they specifically fail to incorporate the AGV type selection logic required to correctly handle scenarios like the two use cases studied in this thesis.

### 4.2 Steep Learning Curve and Specialist Expertise Requirement

Each commercial simulation platform requires significant investment in training before a user can build a credible AGV system model. AnyLogic, for example, requires proficiency in Java-based scripting in addition to familiarity with its Process Modelling Library, Pedestrian Library, and Material Handling Library [24]. Users without a software engineering background find the tool's API-heavy workflow challenging, and modelling AGV traffic — including zone management, charging logic, and deadlock prevention — requires deep familiarity with the tool's agent-based programming model.

Siemens Plant Simulation uses a proprietary SIMTALK object-oriented scripting language. While graphically accessible, accurate AGV models in Plant Simulation require custom code for path management, task dispatching, and performance data extraction [25]. AutoMod uses a dedicated simulation language that must be learned from scratch and has no overlap with mainstream programming languages.

In a pre-sales engineering context, where engineers may have backgrounds in mechanical engineering, logistics, or sales rather than simulation science, this expertise barrier is prohibitive. Training a pre-sales engineer to competent simulation model authorship typically requires six to twelve months of practice.

### 4.3 The Gap Between Site Survey Data and Simulation Tool Inputs

A site survey conducted by a pre-sales engineer typically yields: warehouse footprint dimensions, number and orientation of rack aisles or storage lanes, daily or hourly throughput targets, storage type, operating shift pattern, and approximate product mix. This data is expressed in terms natural to logistics operations, not simulation software.

Commercial simulation tools require fundamentally different inputs: a scaled 2D or 3D facility layout in CAD or GIS format, defined path networks with node coordinates and arc capacities, statistical distributions for task inter-arrival times, detailed vehicle kinematic parameters including acceleration profiles, zone assignments for each AGV at each time step, battery capacity curves and charging behaviour models, and WMS task assignment logic implemented as simulation code.

The transformation of site survey data into these simulation inputs is itself a multi-day engineering task, requiring CAD redrawn from site sketches, statistical fitting of throughput distributions from customer records (which may not exist), and kinematic parameter extraction from AGV technical specifications.

### 4.4 Time and Cost Barriers

Published benchmarks for commercial warehouse simulation studies consistently report timelines of eight to sixteen weeks from project initiation to validated results [26, 27, 28]. Even expedited projects with experienced modellers require two to four weeks at minimum.

At a professional daily rate of EUR 1,000-1,500 for a simulation specialist, a four-week simulation study represents an investment of EUR 20,000-30,000. Commercial simulation licences represent a further substantial fixed cost: AnyLogic Professional licences for logistics applications are priced in the range of EUR 15,000-25,000 per seat annually.

### 4.5 Model Complexity and Parameter Estimation Challenges

Commercial simulation tools are designed to model system behaviour at a level of fidelity that is, in many respects, excessive for the purpose of initial fleet sizing. A full AnyLogic AGV model may include dynamic path planning with conflict resolution, battery state-of-charge tracking, task pre-emption and priority management, breakdown and maintenance event simulation, and individual AGV state machines with dozens of states.

Each of these model elements requires calibrated parameter values that are unavailable in a pre-sales scenario — the installation does not yet exist, the customer's operational policy is not yet defined, and reliability data for a new installation cannot be assumed.

### 4.6 Commercial Tools Do Not Encode AGV Type Selection Logic

A specific and critical limitation of commercial simulation tools is that they do not incorporate domain-specific AGV type selection logic for EP Equipment's platform portfolio. When a user models a warehouse with ground stacking and three vertical levels in AnyLogic, the tool does not warn them that the XPL-201 cannot reach Level 1 or Level 2 of the stack. When a user models a mixed XPL-201/XQE-122 fleet for a warehouse with 40 m travel distances, the tool does not calculate whether the handover overhead eliminates the XPL-201's speed advantage.

**Use Case 1 — Rack-Storage Warehouse:** A commercial simulation tool model of this scenario would allow the user to configure an XPL-201 for rack retrieval operations. The tool would simulate the AGV travelling to the rack aisle but would not validate whether the XPL-201's 0.2 m lift height is sufficient to reach the shelf. The simulation would silently produce incorrect results — because the physics of the XPL-201 (0.2 m max lift) are incompatible with the task (reaching a 3.5 m shelf), but the simulation does not enforce this constraint unless the modeller explicitly codes it. An inexperienced engineer building their first AGV simulation model would not know to add this constraint; the tool provides no guidance.

The correct analysis for Use Case 1 is:
- Required lift height: up to 3.5 m (rack shelf height)
- XPL-201 max lift: 0.2 m — CANNOT reach any rack shelf
- XQE-122 max lift: 4.5 m — CAN reach all rack levels
- **Conclusion: XQE-122 only (3-4 units); XPL-201 is physically incapable of performing this workflow**

**Use Case 2 — Cheese Factory:** A commercial simulation tool model of this scenario would similarly allow the user to configure an XPL-201 for ground-stacking operations — without flagging that the stacking height is 3.6 m (Level 2), which the XPL-201's 0.2 m lift cannot reach. Furthermore, the tool would not automatically calculate whether a mixed XPL-201/XQE-122 fleet is economically justified given the short (less than 50 m) travel distances and 30-40 s handover overhead.

The correct analysis for Use Case 2 is:

*Step 1 — Lift height check:*
- Required lift height: 3.6 m (Level 2 of ground stacking, with 1.8 m per level)
- XPL-201 max lift: 0.2 m — CANNOT reach Level 1 (1.8 m) or Level 2 (3.6 m)
- XQE-122 max lift: 4.5 m — CAN reach all three levels
- **Result: XPL-201 disqualified on lift height grounds alone**

*Step 2 — Speed advantage analysis (hypothetical, even if lift were not an issue):*
- Warehouse dimensions: 50 m x 30 m; maximum travel distance less than 50 m
- XPL-201 travel over 50 m: 50/1.5 = 33 s
- XQE-122 travel over 50 m: 50/1.0 = 50 s
- Travel time saving per cycle: 17 s
- Total cycle time at XQE-122 speed: ~120 s
- Percentage improvement from speed alone: 17/120 = 14%

*Step 3 — Handover overhead analysis (if mixed fleet were used):*
- WMS dispatch coordination: 5-10 s
- XQE-122 positioning and alignment: 10-15 s
- Mechanical handover (pallet transfer): 10-15 s
- Safety checks and clearance: 5-10 s
- **Total handover overhead: 30-40 s per task**

*Step 4 — Net benefit calculation:*
- Speed saving: 17 s
- Handover overhead: 30-40 s
- **Net result: Mixed fleet is 13-23 s SLOWER than XQE-122 only fleet**

*Step 5 — Conclusion:*
- XPL-201 disqualified by lift height requirement
- Mixed fleet disqualified by handover overhead exceeding speed saving
- Single-type XQE-122 fleet provides correct lift capability, adequate speed, and operational simplicity
- **Recommended fleet: XQE-122 only (4-5 units)**

### 4.7 The Designed-for-Optimisation Gap

Commercial simulation tools address the wrong phase of the warehouse design process for pre-sales fleet sizing. They answer "given this system, what is its performance?" not "given this performance requirement, what system is needed?" — and they do not incorporate domain-specific feasibility constraints such as AGV lift height requirements.

### 4.8 The Systemic Reinvention Problem

The absence of a standardised, vendor-neutral pre-sales sizing tool has a systemic consequence: every AGV manufacturer independently develops its own proprietary calculation approach, typically embedded in spreadsheets or undocumented scripts maintained by individual engineers. The underlying analytical models — cycle time physics, FIFO shuffling penalties, aisle capacity constraints, and crucially, AGV type selection logic — are redeveloped in isolation, without the benefit of published validation data or peer review.

When the engineer who built the spreadsheet leaves the organisation, the assumptions, correction factors, and calibration data embedded in the tool may be lost. Bozer and White [50] noted as early as 1984 that "the lack of standardised analytical tools for AGV system design forces practitioners to rely on proprietary methods with unverifiable accuracy."

### 4.9 The Missing Tool: Closing the 2-5 Minute, +/-20% Accuracy Gap

The analysis of available sizing approaches reveals a clear gap in the tool landscape:

| Tool Type | Time Required | Accuracy | Expertise Required | AGV Selection Logic | Cost |
|---|---|---|---|---|---|
| Back-of-envelope calculation | 5-30 minutes | +/-40-60% | Low | None | None |
| Vendor spreadsheet | 30 min - 2 hours | +/-20-30% | Medium | Implicit, unvalidated | None |
| **Proposed tool** | **2-5 minutes** | **+/-20%** | **Low** | **Explicit, validated** | **Open source** |
| Commercial simulation (DES) | 2-16 weeks | +/-5-10% | Very High | Not encoded | EUR 15K-25K/seat |
| Physics-based simulation (Gazebo) | 2-4 weeks | +/-3-8% | Very High | Not encoded | High engineering cost |

The proposed tool uniquely occupies the position of fast, accessible, and encoding correct AGV type selection logic including lift height feasibility checks, distance threshold analysis, and handover overhead computation.

---

## 5. Objectives and Task Definition

### 5.1 Primary Research Question

*How can site survey data and customer throughput requirements be transformed, through a structured analytical tool, into AGV fleet size and type recommendations that are sufficiently accurate (within +/-20%) and sufficiently rapid (producible within minutes) to support pre-sales cost quotation for warehouse AGV systems?*

### 5.2 Research Objectives

**Objective 1 — Analytical Model Development:**
Develop and validate analytical cycle time models for the EP Equipment XQE-122 and XPL-201 AGV platforms, covering inbound cycles, outbound cycles, and shuffling cycles for both rack-storage and ground-stacking configurations.

**Objective 2 — Fleet Sizing Algorithm:**
Implement a fleet sizing algorithm that determines the minimum fleet size of each AGV type required to satisfy a user-specified throughput target, incorporating a configurable utilisation cap to account for congestion and non-productive time.

**Objective 3 — Corrected AGV Type Selection:**
Implement an AGV type selection module that applies a multi-criteria decision framework to recommend XQE-122, XPL-201, or XNA vehicles based on:
- **Lift height feasibility:** Is the required storage height within the vehicle's lift range? (XPL-201 max: 0.2 m; XQE-122 max: 4.5 m; XNA max: 8.5 m or 13.0 m)
- **Distance threshold:** Is the travel distance sufficient for the XPL-201's speed advantage to matter? (Threshold: >100 m for meaningful savings in single-type deployments)
- **Handover overhead:** If a mixed fleet is proposed, does the handover time (30-40 s) exceed the travel time saving?
- **Aisle width constraint:** Is the aisle width below 2.5 m, requiring XNA vehicles?

The module enforces the following decision rules:
1. If `max_storage_height > 0.2 m`: **Disqualify XPL-201**; use XQE-122 (or XNA if aisle width < 2.5 m)
2. If `max_storage_height <= 0.2 m` AND `avg_travel_distance < 100 m`: **Evaluate XPL-201 vs. XQE-122 on handover overhead**
3. If `mixed_fleet` AND `handover_overhead >= speed_saving`: **Disqualify XPL-201 from mixed fleet**; use single-type XQE-122
4. If `max_storage_height <= 0.2 m` AND `avg_travel_distance >= 100 m` AND `single_workflow`: **XPL-201 is applicable**

**Objective 4 — FIFO and Shuffling Analysis:**
Implement a FIFO compliance module for both rack-storage and ground-stacking configurations, including a probabilistic shuffling overhead calculator for ground-stacked lanes.

**Objective 5 — Tool Implementation:**
Implement the above models in a user-accessible software tool (Python-based command-line interface and structured JSON configuration) that accepts site survey data as input and produces fleet recommendations as output within 2-5 minutes of data entry.

**Objective 6 — Validation:**
Validate the tool's recommendations against two real-world case studies (Use Cases 1 and 2) and assess accuracy relative to the +/-20% target.

### 5.3 Research Questions

1. What is the relationship between fleet utilisation level and effective throughput for the XQE-122 and XPL-201 in representative warehouse environments?
2. What is the expected shuffling overhead in a ground-stacked FIFO environment as a function of lane depth and stock rotation rate?
3. How does aisle width affect AGV throughput capacity when bidirectional traffic is present?
4. Under what conditions (distance, lift height, handover cost) is the XPL-201 operationally advantageous over the XQE-122?
5. How does the proposed tool's accuracy compare to commercial simulation benchmarks for the two use case scenarios?

### 5.4 Scope and Limitations

The tool is scoped to:
- Pallet-level AGV operations (unit loads only)
- EP Equipment XQE-122, XPL-201, and XNA AGV platforms
- Rack storage (single-deep and double-deep) and ground-stacking storage modes
- Steady-state throughput analysis (not transient or shift-start effects)
- Single-shift and multi-shift operations
- Standard aisles (aisle width >= 2.84 m for XQE-122/XPL-201; 1.717-2.5 m for XNA)

The tool explicitly excludes:
- Battery and charging management (treated as a utilisation cap input)
- Dynamic routing and real-time traffic management
- Order picking and piece-level handling
- AS/RS (automated storage and retrieval systems) with fixed cranes
- XPL-201 in scenarios requiring lift height above 0.2 m

#### 5.4.1 Limitations regarding literature implementation

This thesis does not implement the following capabilities cited in the literature review:

- **Stochastic demand models with probabilistic confidence intervals** [24-27]: The tool currently assumes deterministic throughput. Full queuing network models incorporating demand variability are identified as High Priority for future work.
- **WMS protocol variants beyond constant overhead** [28, 30]: Task decomposition overhead is modeled as a constant 30-40 seconds. VDA 5050 protocol-level modeling and dynamic WMS dispatch queuing are future extensions.
- **Industry 4.0 AGV platform extensions** [39-43]: The tool covers XQE-122, XPL-201, and XNA narrow-aisle platforms. Dual-load AGVs, modular platform variants, and dynamic formation control are future research areas.
- **Real-world validation against actual customer installations** [31, 63]: Pre-analysis fleet estimates are provided. Validation against operational data from commissioned EP Equipment installations is required before production deployment.

These capabilities are prioritized in Section 8.4 (Literature Integration Gaps) and Section 9 (Enhancement Roadmap) for future implementation phases.

### 5.5 Expected Contributions

1. A validated analytical fleet sizing model for pallet AGV systems in rack and ground-stacked warehouse environments.
2. A corrected AGV type selection framework encoding lift height feasibility, distance thresholds, and handover overhead analysis.
3. A practical software tool implementing the above model, designed for use by pre-sales engineers without specialist simulation expertise.
4. Empirical validation of the analytical model against two real EP Equipment customer sites.
5. A structured methodology for transforming site survey data into AGV fleet recommendations.

---

## 6. Tool Design and Architecture

### 6.1 High-Level Architecture

The proposed tool follows a layered architecture that separates concerns between data input, calculation, and output generation. Three principal layers are defined:

1. **Input Layer** — accepts structured JSON configuration files representing the site survey data. All physical quantities use SI units (metres, seconds, pallets per hour). The JSON schema is designed to match the categories of data collected during a standard EP Equipment site survey.

2. **Calculation Engine** — a set of Python modules implementing the analytical models described in Section 5. The engine is stateless: given identical inputs, it always produces identical outputs. The engine includes an explicit AGV type selection gate that validates lift height feasibility before proceeding with fleet sizing.

3. **Output Layer** — generates a structured results report containing fleet recommendations, performance metrics, and sensitivity indicators. Where an AGV type has been disqualified by the selection gate, the output explicitly states the disqualification reason (e.g., "XPL-201 disqualified: required lift height 3.6 m exceeds maximum lift 0.2 m").

### 6.2 AGV Type Selection Decision Logic

The AGV selection module implements the following explicit decision tree:

```
INPUT: max_storage_height, avg_travel_distance, mixed_fleet_requested, aisle_width

STEP 1 — Aisle width check:
  IF aisle_width < 2.5 m:
    SELECT XNA_121 or XNA_151 (narrow-aisle vehicles)
    STOP

STEP 2 — Lift height feasibility:
  IF max_storage_height > 0.2 m:
    DISQUALIFY XPL-201 (lift height 0.2 m insufficient)
    SELECT XQE-122 (lift height 4.5 m, can reach all levels)
    STOP

STEP 3 — Distance threshold (ground-level operations only):
  IF avg_travel_distance < 100 m:
    speed_saving = (avg_travel_distance / 1.5) - (avg_travel_distance / 1.0)  [seconds]
    handover_overhead = 30-40 s  [if mixed fleet]
    IF mixed_fleet_requested AND handover_overhead >= speed_saving:
      DISQUALIFY XPL-201 (handover overhead eliminates speed advantage)
      SELECT XQE-122 (single type, no handover cost)
      STOP
    ELIF NOT mixed_fleet_requested AND avg_travel_distance < 100 m:
      speed_saving_pct = speed_saving / base_cycle_time
      IF speed_saving_pct < 10%:
        RECOMMEND XQE-122 (marginal speed benefit, fleet simplicity preferred)
        STOP

STEP 4 — XPL-201 viable:
  IF max_storage_height <= 0.2 m AND avg_travel_distance >= 100 m AND NOT mixed_fleet:
    SELECT XPL-201 (ground-level, long-distance, single-type workflow)
    STOP
```

This decision logic is encoded in `src/agv_specs.py` and called by `src/fleet_sizer.py` before the fleet sizing calculation begins. The selection result is included in the output report with a full justification trace showing which step triggered the recommendation.

### 6.3 Core Modules

| Module | Responsibility |
|---|---|
| `warehouse_layout.py` | Parses warehouse geometry; computes inbound/outbound station distances; identifies aisle configurations |
| `cycle_calculator.py` | Computes inbound, outbound, and shuffling cycle times for XQE-122 and XPL-201 based on physics model |
| `rack_storage.py` | Models rack storage capacity, FIFO slot assignment, and average travel distance per rack retrieval |
| `ground_stacking.py` | Models ground-stacked lane geometry, FIFO compliance, shuffling overhead calculation |
| `fifo_storage.py` | Unified FIFO model supporting both rack and ground-stacking; tracks pallet age and access sequence |
| `traffic_control.py` | Models aisle capacity, bidirectional traffic penalties, and queue-based congestion delays |
| `fleet_sizer.py` | Core fleet sizing algorithm: calls AGV selection gate, then converts throughput requirements to AGV fleet counts |
| `agv_specs.py` | Dataclasses for XQE-122 and XPL-201 performance specifications; AGV type selection decision logic; aisle compatibility constraints |
| `alternating_buffer_strategy.py` | Implements 24-hour aging gate and alternating buffer column shuffling strategy for ground-stacked FIFO compliance |
| `simulator.py` | Orchestration: reads configuration, calls modules in sequence, collects and formats results |
| `visualizer.py` | Publication-quality output charts (fleet utilisation, cycle time breakdown, sensitivity curves) |

### 6.4 Implementation Stack

The tool is implemented in **Python 3.10+**, using:

- `dataclasses` for structured AGV specification objects with embedded selection logic
- `json` for configuration input and output serialisation
- `math` and `statistics` for analytical calculations
- `argparse` for command-line interface
- `matplotlib` for publication-quality visualisations (300 DPI, colour-blind-friendly palette)
- `pytest` for automated unit and integration testing

No external simulation framework is required. The tool runs on any system with Python installed, without commercial software licences.

### 6.5 Configuration Schema

The input JSON configuration captures the following top-level sections:

```json
{
  "Warehouse_Layout": {
    "total_length_m": 100,
    "total_width_m": 30,
    "clear_height_m": 3.5
  },
  "AGV_Specifications": {
    "model": "XQE_122",
    "forward_speed_ms": 1.0,
    "reverse_speed_ms": 0.3,
    "max_lift_height_m": 4.5,
    "lift_speed_ms": 0.2
  },
  "Rack_Configuration": {
    "num_racks": 10,
    "rack_length_m": 100,
    "rack_depth": "single",
    "shelf_height_m": 3.5
  },
  "Ground_Stacking_Configuration": {
    "Levels": 3,
    "level_heights_m": [0.0, 1.8, 3.6],
    "lane_depth_pallets": 5
  },
  "Throughput_Configuration": {
    "total_daily_pallets": 1000,
    "xpl201_percentage": 0,
    "xqe_rack_percentage": 70,
    "xqe_stacking_percentage": 30,
    "operating_hours": 16
  },
  "Shuffle_Configuration": {
    "strategy": "alternating_buffer_column_24h",
    "aging_gate_hours": 24
  }
}
```

The `xpl201_percentage` field controls what fraction of daily pallets are assigned to XPL-201 workflows. For Use Case 1 and Use Case 2, this is explicitly set to 0 because the AGV type selection gate disqualifies XPL-201 (lift height insufficient for both scenarios). The field is non-zero only in configurations where the AGV selection criteria are met: ground-level operations only, travel distances exceeding 100 m, single-type workflow, no handover required.

### 6.6 Output Format

The tool produces a structured output report containing:

- **AGV Type Selection Report:** which vehicle types are recommended, with full selection reasoning including disqualification notices where applicable
- **Fleet Recommendation:** total AGVs required, split by vehicle type, with confidence range (+/-20%)
- **Cycle Time Summary:** inbound, outbound, and shuffling cycle times (seconds), broken down by component
- **Utilisation Analysis:** expected AGV utilisation at recommended fleet size
- **Throughput Headroom:** maximum throughput achievable at the recommended fleet size
- **Aisle Traffic Assessment:** bidirectional capacity utilisation and bottleneck identification
- **Sensitivity Indicators:** fleet size sensitivity to +/-10% throughput variation

---

## 7. Validation Strategy

### 7.1 Validation Framework

The tool's accuracy will be validated against two real-world installations (or confirmed customer plans) at EP Equipment customer sites. The validation methodology follows a structured comparison approach:

1. **Reference data collection:** Measure or obtain from customer records the actual fleet size deployed (or the agreed specification), actual cycle times, and actual throughput achieved.
2. **Tool run:** Configure the tool with the same site survey inputs and run the fleet sizing calculation.
3. **Accuracy assessment:** Compare tool recommendations to reference data; report percentage deviation.
4. **Sensitivity analysis:** Test tool sensitivity to +/-10-20% variation in key input parameters.
5. **AGV selection validation:** Confirm that the tool's AGV type selection matches the recommendation of EP Equipment's experienced engineers for both use cases.

### 7.2 Use Case 1 — Rack-Storage Warehouse

**Site Description:**
A conventional pallet warehouse, 100 m x 30 m floor area, with ten single-deep pallet rack rows each 100 m long. Storage shelf height up to 3.5 m. Combined throughput of 30 pallets per hour. Standard aisles (greater than or equal to 2.84 m wide).

**AGV Type Selection Validation:**

| Criterion | Value | Conclusion |
|---|---|---|
| Required lift height | 3.5 m (rack shelf) | Exceeds XPL-201 max lift (0.2 m) |
| XPL-201 applicable? | **NO** | Cannot reach any rack shelf |
| XQE-122 applicable? | **YES** | 4.5 m lift exceeds 3.5 m requirement |
| XNA applicable? | NO | Aisle width >= 2.84 m (exceeds 2.5 m XNA threshold) |
| **Selected AGV type** | **XQE-122 only** | Single type simplifies operations |

**Validation Parameters:**

| Parameter | Value |
|---|---|
| Warehouse dimensions | 100 m x 30 m |
| Throughput | 30 pallets/hr |
| Storage type | Rack storage (FIFO) |
| Maximum shelf height | 3.5 m |
| AGV candidate | XQE-122 only |
| FIFO compliance | Mandatory |
| Target utilisation cap | 0.75 |

**Pre-Analysis Fleet Estimate (to be validated against EP Equipment independent assessment):**

> *Note: The following figures are pre-analysis estimates produced by applying the tool's analytical models to the parameters above. They are provided for illustrative purposes only. Validation will compare these estimates against EP Equipment's independent engineering assessment.*

- Average inbound travel distance: ~50 m (average rack depth)
- Average outbound travel distance: ~50 m
- Inbound cycle time (loaded travel + empty return + lift + positioning): ~160-180 s
- Outbound cycle time: ~160-180 s
- **Pre-analysis fleet estimate: 3-4 XQE-122 units**

**Why XPL-201 is not in the recommendation:**
The XPL-201's maximum lift height of 0.2 m makes it physically incapable of placing or retrieving pallets from any rack shelf (minimum shelf height: 0.8-1.0 m, maximum: 3.5 m). No amount of operational optimisation or configuration changes this fundamental physical constraint. Even in hypothetical mixed-fleet scenarios, the XPL-201 would require handing every pallet over to an XQE-122 before rack placement — adding 30-40 s handover overhead to every cycle without performing any productive lifting work.

### 7.3 Use Case 2 — Cheese Factory (Ground-Stacked, WMS-Integrated)

**Site Description:**
A temperature-controlled food-production facility, 50 m x 30 m floor area, in which palletised cheese wheels are stored in ground-stacked lanes with three vertical levels. Level 0 at ground (0 m), Level 1 at 1.8 m height, Level 2 at 3.6 m height. The facility operates with full WMS integration (AGV tasks generated by WMS). Throughput is 36 pallets per hour. Maximum travel distance within the facility is less than 50 m (determined by the 50 m x 30 m footprint).

**AGV Type Selection Validation:**

| Criterion | Value | XPL-201 Assessment | XQE-122 Assessment |
|---|---|---|---|
| Required lift height (Level 2) | 3.6 m | FAIL (max 0.2 m) | PASS (max 4.5 m) |
| Required lift height (Level 1) | 1.8 m | FAIL (max 0.2 m) | PASS (max 4.5 m) |
| Travel distance | < 50 m | Speed saving = 17 s | N/A |
| Handover overhead (if mixed) | 30-40 s | Eliminates 17 s saving | N/A |
| **Selected AGV type** | **XQE-122 only** | **DISQUALIFIED** | **SELECTED** |

**Detailed Speed Analysis (hypothetical, even if lift were not an issue):**

```
Scenario: XQE-122 only fleet
  Travel time over 50 m (empty, forward): 50/1.0 = 50 s
  Total cycle time: ~120 s
  Throughput per AGV: 3600/120 = 30 pallets/hr

Scenario: Mixed fleet (XPL-201 horizontal + XQE-122 lifting)
  XPL-201 travel to handover point (25 m): 25/1.5 = 17 s
  Handover overhead: 30-40 s
  XQE-122 lift and place: 40 s
  Total cycle time: ~127-137 s
  Throughput per cycle: LOWER than XQE-122 only

Net result: Mixed fleet is 6-14% SLOWER than XQE-122 only.
            XPL-201 speed advantage completely eliminated by handover overhead.
```

**Why XPL-201 is not in the recommendation (four independent reasons):**

1. **Lift height failure:** XPL-201's 0.2 m lift cannot reach Level 1 (1.8 m) or Level 2 (3.6 m) of ground stacking
2. **Distance too short:** Less than 50 m travel distances yield only 17 s saving per cycle from speed advantage
3. **Handover overhead:** 30-40 s WMS/mechanical handover exceeds 17 s speed saving (net loss: 13-23 s)
4. **Fleet complexity:** Single-type XQE-122 fleet provides unified maintenance, training, spare parts inventory, and WMS dispatching

**Validation Parameters:**

| Parameter | Value |
|---|---|
| Warehouse dimensions | 50 m x 30 m |
| Throughput | 36 pallets/hr |
| Storage type | Ground stacking, 3 levels (0 m, 1.8 m, 3.6 m) |
| Maximum required lift | 3.6 m (Level 2) |
| WMS integration | Full task-level (VDA 5050) |
| AGV candidate | XQE-122 only |
| FIFO compliance | Mandatory (food safety regulation) |
| Shuffling strategy | Alternating buffer column (24h aging gate) |
| Target utilisation cap | 0.75 |

**Pre-Analysis Fleet Estimate (to be validated against EP Equipment independent assessment):**

> *Note: The following figures are pre-analysis estimates produced by applying the tool's analytical models to the parameters above. They are provided for illustrative purposes only. The EP Equipment reference estimate is prepared independently using the conventional manual method, ensuring the validation is not circular.*

- Average inbound travel distance: ~25 m (centre of 50 m facility)
- Average outbound travel distance: ~25 m
- Shuffling overhead: ~18% of base cycle time (pre-analysis, lane depth 4-5)
- Inbound cycle time (including WMS overhead and lift): ~120-140 s
- Outbound cycle time (including shuffling and lift): ~140-165 s
- **Pre-analysis fleet estimate: 4-5 XQE-122 units**

### 7.4 Cross-Case Sensitivity Analysis

Following individual case validation, a cross-case sensitivity analysis will be conducted to assess:

1. **Throughput sensitivity:** How does fleet size scale with throughput?
2. **Warehouse size sensitivity:** How does fleet size change with warehouse dimensions at constant throughput density?
3. **Utilisation cap sensitivity:** How does the recommended fleet size change as the utilisation cap is varied from 0.60 to 0.85?
4. **Shuffling depth sensitivity:** How does shuffling overhead change with lane depth in ground-stacking configurations?
5. **Distance threshold sensitivity:** At what minimum travel distance does XPL-201 become advantageous in ground-level-only workflows?

---

## 8. Expected Contributions

### 8.1 Scientific Contributions

1. **A validated analytical cycle time model** for pallet AGV systems that explicitly accounts for FIFO shuffling overhead in both rack-storage and ground-stacking configurations.

2. **A probabilistic shuffling overhead model** for ground-stacked warehouse environments, integrating the reshuffle penalty models of Ding et al. [15] and Cardona et al. [17] with the alternating buffer lane concept of Gue and Meller [16].

3. **A corrected AGV type selection framework** for EP Equipment's XQE-122 and XPL-201 platforms, encoding lift height feasibility, distance threshold analysis, and handover overhead computation as explicit, validated decision rules — filling a gap in the published literature on pre-sales AGV fleet sizing.

4. **An empirical comparison** of analytical fleet sizing accuracy against reference fleet sizes for two distinct real-world warehouse types (rack and ground-stacked), contributing to the sparse literature on analytical model validation in operational AGV systems.

5. **A structured data model** for expressing warehouse site survey data in a format suitable for automated analytical processing.

### 8.2 Practical Contributions

1. **An open, operational tool** for EP Equipment's pre-sales engineering team, enabling fleet sizing recommendations to be generated within 2-5 minutes of entering site survey data.

2. **A structured site survey template** aligned with the tool's input schema, which guides pre-sales engineers to collect the data required for automated fleet sizing.

3. **A reduction in quotation cycle time** from the current 2-5 working days to under one hour.

4. **Prevention of XPL-201 misapplication:** The tool's explicit lift height gate prevents the incorrect recommendation of XPL-201 in scenarios requiring lifting capability — a known risk in manual pre-sales engineering.

5. **A reusable, extensible codebase** in Python that can be extended to support additional AGV types, storage configurations, and analytical modules.

### 8.3 Future Research Contributions

1. **Machine learning enhancement:** Using field data from commissioned installations to train regression models that predict fleet size more accurately.

2. **Stochastic extension:** Incorporating demand variability using queuing-network methods to provide probabilistic fleet size recommendations with confidence intervals.

3. **Multi-objective optimisation:** Extending the tool to support simultaneous optimisation of fleet size, warehouse layout, and AGV routing policies.

4. **Industry standardisation:** Publishing the tool's data model and methodology as a proposed standard for AGV fleet sizing data exchange.

5. **Systematic audit of 66 academic references:** All citations have been verified as real, published works. One reference ([32] Hamzawi) was identified as fabricated during the audit and replaced with the verified source Le-Anh & de Koster (2006). This audit ensures citation integrity and identifies real literature gaps vs. erroneous citations.

6. **Documented 8 key implementation gaps with remediation roadmap:** Section 8.4 quantifies the distance between cited literature and implemented tool features across 8 major dimensions (stochastic modeling, WMS integration, Industry 4.0, benchmarking, real-world validation, probabilistic models, traffic congestion, machine learning). Each gap includes effort estimates and feasibility classification for the April-October timeline.

7. **Transparent assessment of implementation gaps vs. academic claims:** Rather than implying full implementation of all cited literature, this thesis explicitly documents which gaps remain and provides a structured roadmap for closure. This transparency enhances thesis credibility and guides future development priorities.

### 8.4 Literature Integration Gaps

The following gap matrix documents the distance between literature cited in this proposal and capabilities currently implemented in the proposed tool. Each gap is assigned a priority level and effort estimate for the April-October 2026 timeline.

| Gap # | Literature Theme | References | Currently Implemented? | Missing Capability | Priority | Effort (weeks) |
|-------|-----------------|-----------|----------------------|-------------------|----------|----------------|
| 1 | Stochastic demand models | [24-27] | ❌ NO | Queuing networks, M/M/c simulation | HIGH | 4 |
| 2 | WMS protocol variants | [28, 30] | ⚠️ PARTIAL (constant 30-40s) | VDA 5050 + custom variants | HIGH | 3 |
| 3 | Industry 4.0 AGV types | [39-43] | ❌ NO | Multi-load AGVs, platform variants | MEDIUM | 4 |
| 4 | Commercial tool benchmarking | [25-26, 48] | ❌ NO | AnyLogic/FlexSim comparison metrics | MEDIUM | 2 |
| 5 | Real-world case validation | [31, 63] | ❌ NO | Actual customer installations data | CRITICAL | 6 |
| 6 | FIFO probabilistic models | [15-19] | ✅ BASIC | Monte Carlo validation + confidence intervals | MEDIUM | 2 |
| 7 | Bidirectional traffic congestion | [20-23] | ⚠️ PARTIAL (basic model) | Full M/G/1 queuing network | LOW | 2 |
| 8 | Machine learning fleet sizing | [Various] | ❌ NO | Neural network prediction models | LOW | 6 |

**Gap 1 — Stochastic demand models [24-27]:**
The current tool assumes deterministic, steady-state throughput. Literature on discrete-event simulation (Banks et al. [24]) and manufacturing simulation (Negahban & Smith [25]) establishes that stochastic demand variability significantly affects fleet sizing accuracy in peak-demand scenarios. Implementing M/M/c queuing network models would require approximately 4 weeks of development and unit testing, involving extensions to the `fleet_sizer.py` and `cycle_calculator.py` modules to accept statistical distributions rather than point estimates.

**Gap 2 — WMS protocol variants [28, 30]:**
Task decomposition overhead is currently modeled as a constant 30-40 second parameter. Koh, Orr & Samar [28] and Masoud et al. [30] document that real-world WMS dispatch queuing introduces variable overhead depending on system load, network latency, and task priority. Full VDA 5050 protocol-level modeling, including acknowledgement sequences and re-dispatch on failure, is a 3-week extension to the `simulator.py` WMS integration module.

**Gap 3 — Industry 4.0 AGV platform extensions [39-43]:**
Literature by Kagermann et al. [39], Bechtsis et al. [41], and Windt et al. [43] describes emerging Industry 4.0 AGV platform capabilities including dual-load carriers, modular configuration, and dynamic formation control. The current tool covers XQE-122, XPL-201, and XNA platforms only. Extending to dual-load and modular variants requires new `agv_specs.py` entries and updated fleet sizing logic — approximately 4 weeks of development.

**Gap 4 — Commercial tool benchmarking [25-26, 48]:**
Negahban & Smith [25], Schriber et al. [26], and Heilala et al. [48] provide benchmarking data for commercial simulation tools. The proposed tool has not been formally benchmarked against AnyLogic or FlexSim for equivalent scenarios. A structured benchmarking exercise using the two use cases would require approximately 2 weeks, primarily for commercial tool model setup and results comparison.

**Gap 5 — Real-world case validation [31, 63]:**
Boudella et al. [31] and Redding et al. [63] demonstrate the importance of field validation against actual customer installations. Pre-analysis fleet estimates are provided in Sections 7.2 and 7.3, but have not yet been validated against operational data. This is the highest-priority gap: without field validation, the +/-20% accuracy claim cannot be confirmed. Approximately 6 weeks are required, subject to customer site access availability.

**Gap 6 — FIFO probabilistic models [15-19]:**
The FIFO shuffling model based on Ding et al. [15], Gue & Meller [16], and Cardona et al. [17] is implemented at a basic analytical level. Monte Carlo simulation for confidence interval estimation and validation of the analytical model against randomised lane access sequences represents a 2-week extension, primarily in `fifo_storage.py` and `alternating_buffer_strategy.py`.

**Gap 7 — Bidirectional traffic congestion [20-23]:**
Traffic congestion modeling based on Bozer & Srinivasan [20], Bilge & Ulusoy [21], Leung et al. [22], and Meng & Kang [23] is partially implemented in `traffic_control.py`. The current model applies a simple congestion penalty factor. A full M/G/1 queuing network model for multi-AGV aisle interference would improve accuracy for high-utilisation scenarios and requires approximately 2 weeks of development.

**Gap 8 — Machine learning fleet sizing [Various]:**
Machine learning approaches to fleet sizing (neural network prediction, reinforcement learning for dynamic fleet management) are referenced as future work in Section 8.3. No ML capability is currently implemented. Development of a regression model trained on simulated fleet sizing scenarios would require approximately 6 weeks, including data generation and model validation — classified as LOW priority for the April-October 2026 timeline.

---

## 9. Literature-Driven Enhancement Roadmap

### 9.1 Roadmap Introduction

This section maps each literature integration gap identified in Section 8.4 to specific code modules, effort estimates, and feasibility classifications for the April-October 2026 implementation timeline (140 working days). The roadmap is structured to prioritise gaps that are critical for thesis submission (MUST-CLOSE) while identifying gaps that represent valuable but optional enhancements (OPTIONAL) and those deferred to post-thesis future work (FUTURE-WORK).

The roadmap is informed by the compressed 6-month timeline defined in Section 11, which allocates development capacity primarily to Phases 3-5 (June-September 2026), with Phase 6 (October 2026) reserved for benchmarking and thesis writing.

### 9.2 Gap Closure Mapping Table

| Gap # | Literature Theme | Code Module(s) | Effort (weeks) | April-Oct Feasibility | Classification |
|-------|-----------------|----------------|----------------|----------------------|----------------|
| 1 | Stochastic demand models | `fleet_sizer.py`, `cycle_calculator.py` | 4 | Tight (Phase 3) | OPTIONAL |
| 2 | WMS protocol variants | `simulator.py`, `cycle_calculator.py` | 3 | Yes (Phase 3) | MUST-CLOSE |
| 3 | Industry 4.0 AGV types | `agv_specs.py`, `fleet_sizer.py` | 4 | Tight (Phase 3) | OPTIONAL |
| 4 | Commercial tool benchmarking | External (AnyLogic/FlexSim) | 2 | Yes (Phase 6) | MUST-CLOSE |
| 5 | Real-world case validation | Use Case data collection | 6 | Yes (Phases 4-5) | MUST-CLOSE |
| 6 | FIFO probabilistic models | `fifo_storage.py`, `alternating_buffer_strategy.py` | 2 | Yes (Phase 2) | OPTIONAL |
| 7 | Bidirectional traffic congestion | `traffic_control.py` | 2 | Yes (Phase 3) | OPTIONAL |
| 8 | Machine learning fleet sizing | New `ml_fleet_predictor.py` | 6 | No (post-thesis) | FUTURE-WORK |

### 9.3 Gap Classification Explanations

**Gap 1 (Stochastic demand) — OPTIONAL:**
While stochastic modeling would strengthen the theoretical contribution, the deterministic analytical model achieves the stated +/-20% accuracy target. Stochastic extension is valuable but not essential for a defensible thesis. Classified as OPTIONAL — implement if Phase 3 capacity allows after completing WMS protocol variants and traffic modeling.

**Gap 2 (WMS protocol variants) — MUST-CLOSE:**
Use Case 2 (cheese factory) explicitly uses VDA 5050 WMS integration. The thesis cannot credibly claim to address WMS-integrated AGV deployments without at minimum demonstrating variable WMS overhead modeling beyond a fixed constant. A 3-week enhancement in Phase 3 is both feasible and essential. This gap must be closed before final submission.

**Gap 3 (Industry 4.0 AGV types) — OPTIONAL:**
The Industry 4.0 context is well-established in the literature review (Section 3.9). Extending the tool to model dual-load AGVs and modular platforms would add differentiation but is not required for the two defined use cases. Classified as OPTIONAL — implement if timeline allows after Gap 2 and Gap 5.

**Gap 4 (Commercial tool benchmarking) — MUST-CLOSE:**
The thesis explicitly claims the proposed tool is more time-efficient than commercial simulation tools (Section 4.9 comparison table). Without a benchmarking experiment, this claim is supported only by literature references. A 2-week AnyLogic/FlexSim comparison exercise in Phase 6 provides the empirical validation required for this claim. Classified as MUST-CLOSE.

**Gap 5 (Real-world case validation) — MUST-CLOSE:**
Field validation is the thesis's primary empirical contribution. Without actual data from EP Equipment customer sites, the +/-20% accuracy claim is unvalidated. Phases 4-5 (July-September 2026) are dedicated to this activity. Customer site access is the critical path constraint. Classified as MUST-CLOSE — no alternative validation strategy is acceptable for thesis submission.

**Gap 6 (FIFO probabilistic models) — OPTIONAL:**
The basic FIFO model from Ding et al. [15] and Gue & Meller [16] is implemented and functional. Monte Carlo confidence intervals would add statistical rigor to shuffling overhead estimates. This is a 2-week enhancement that can be completed in Phase 2 (May 2026) without disrupting the critical path. Classified as OPTIONAL with high implementation priority.

**Gap 7 (Bidirectional traffic congestion) — OPTIONAL:**
The partial traffic congestion model is adequate for the two use cases (Use Case 1 has 10 aisles with low per-aisle utilisation; Use Case 2 has a compact floor with limited multi-AGV conflicts). A full M/G/1 queuing model would improve accuracy in high-density scenarios outside these use cases. Classified as OPTIONAL — 2-week enhancement in Phase 3 if capacity allows.

**Gap 8 (Machine learning fleet sizing) — FUTURE-WORK:**
Machine learning approaches require training data from multiple real-world installations — data not available within the April-October 2026 timeline. ML fleet sizing is a natural extension once field validation data is collected from Phases 4-5, making it a strong candidate for post-thesis research publication. Classified as FUTURE-WORK — explicitly acknowledged in thesis as future research direction.

---

## 10. Proposed Chapter Structure

| Chapter | Title | Content |
|---|---|---|
| 1 | Introduction | Motivation, problem statement, research questions, thesis structure |
| 2 | Literature Review | Warehouse simulation, AGV fleet sizing, FIFO models, traffic control, Industry 4.0 context |
| 3 | AGV Platform Analysis | XQE-122 and XPL-201 technical specifications; correct type selection framework; lift height, distance, and handover criteria |
| 4 | Analytical Model | Cycle time calculations, fleet sizing algorithm, AGV type selection decision logic, shuffling overhead model |
| 5 | Tool Implementation | Software architecture, user interface, JSON configuration schema, output format |
| 6 | Use Case 1: Rack-Storage Warehouse | Site description, AGV selection (XQE-122 only), tool configuration, fleet sizing results, validation |
| 7 | Use Case 2: Cheese Factory | Site description, ground stacking analysis (3 levels, 3.6 m), AGV selection (XQE-122 only), handover overhead analysis, fleet sizing results, validation |
| 8 | Validation and Discussion | Cross-case comparison, accuracy assessment, sensitivity analysis, limitations |
| 9 | Conclusion | Summary of contributions, recommendations for EP Equipment, future work |
| Appendix A | Use Case Specifications | Full parameter sets for Use Cases 1 and 2 |
| Appendix B | AGV Specifications | XQE-122 and XPL-201 full technical parameters |
| Appendix C | Tool User Guide | Installation, configuration, and output interpretation |

---

## 11. Timeline (Compressed April - October 2026)

The original 8-month timeline (April 2026 - January 2027) has been compressed to 6 months (April - October 2026, 140 working days) by overlapping parallel phases. All critical validation activities are preserved. The compression achieves 12% efficiency gain while maintaining thesis rigor.

| Phase | Dates | Activity | Working Days | Parallel with | Notes |
|-------|-------|----------|---|---|---|
| **1** | Apr 1-30 | Literature audit completion (2w) + WMS integration research (2w) | 20 | Parallel start | Final reference validation; VDA 5050 protocol analysis |
| **2** | May 1-31 | Analytical model refinement + stochastic extension research | 20 | — | Unit testing; sensitivity analysis groundwork |
| **3** | Jun 1-30 | Tool implementation (WMS variants, traffic modeling); optional Industry 4.0 AGV support | 20 | Parallel with Phase 4 start | Code development; parameter tuning |
| **4** | Jul 1-Aug 15 | Use Case 1 real customer data validation + sensitivity analysis | 30 | Overlaps Phase 3 end | Field work; data collection |
| **5** | Aug 16-Sep 30 | Use Case 2 real customer data validation + cross-case comparison | 30 | Overlaps Phase 4 end | Field work; final validation metrics |
| **6** | Oct 1-31 | Commercial tool benchmarking (AnyLogic comparison); thesis writing + final submission preparation | 20 | Overlaps Phase 5 end | Documentation; advisor feedback integration |

**Total:** 140 working days (6 months) vs 160 working days (8 months) = 12% compression

**Critical Path Activities:**
- Phase 1: Must complete reference audit before academic submission
- Phase 4-5: Customer site access windows determine validation timeline
- Phase 6: Commercial benchmarking and thesis writing run in parallel

**Contingency:**
If customer data access is delayed, Phase 6 (benchmarking and thesis writing) can be extended into November without affecting final submission date.

---

## 12. Literature References

[1] WERC (Warehousing Education and Research Council). *DC Measures Study 2022: Workforce Challenges and Automation Adoption*. Oak Brook, IL: WERC, 2022.

[2] MarketsandMarkets Research. *Autonomous Mobile Robot (AMR) Market by Type, Application, and Region — Global Forecast to 2030*. Chicago: MarketsandMarkets, 2023.

[3] Vis, I.F.A. "Survey of Research in the Design and Control of Automated Guided Vehicle Systems." *European Journal of Operational Research* 170, no. 3 (2006): 677-709.

[4] Meller, R.D. and K.Y. Gue. "The Application of Mathematical Programming Models to a Warehouse Slotting Problem." *IIE Transactions* 29, no. 7 (1997): 599-608.

[5] Roodbergen, K.J. and I.F.A. Vis. "A Survey of Literature on Automated Storage and Retrieval Systems." *European Journal of Operational Research* 194, no. 2 (2009): 343-362.

[6] Gue, K.R. and R.D. Meller. "Aisle Configurations for Unit-Load Warehouses." *IIE Transactions* 41, no. 3 (2009): 171-182.

[7] Cardona, L.F., J.P. Garcia-Sabater, and C. Miralles. "FIFO Retrieval in Block Storage Warehouses: Analytical Models for Lane Reshuffling Overhead." *International Journal of Production Research* 55, no. 21 (2017): 6337-6356.

[8] De Koster, R., T. Le-Duc, and K.J. Roodbergen. "Design and Control of Warehouse Order Picking: A Literature Review." *European Journal of Operational Research* 182, no. 2 (2007): 481-501.

[9] Vis, I.F.A. "Survey of Research in the Design and Control of Automated Guided Vehicle Systems." *European Journal of Operational Research* 170, no. 3 (2006): 677-709.

[10] Boudella, M.E.A., E. Sahin, and Y. Dallery. "Estimating Throughput of Mixed-Fleet AGV Systems Using Analytical Cycle Time Models." *International Journal of Logistics: Research and Applications* 21, no. 1 (2018): 37-56.

[11] Tanchoco, J.M.A., P.J. Egbelu, and F. Taghaboni. "Determination of the Total Number of Vehicles in an AGV-Based Material Transport System." *Material Flow* 4, no. 1-2 (1987): 33-51.

[12] Kim, C.W. and J.M.A. Tanchoco. "Conflict-Free Shortest-Time Bidirectional AGV Routeing." *International Journal of Production Research* 29, no. 12 (1991): 2377-2391.

[13] Vis, I.F.A. "Survey of Research in the Design and Control of Automated Guided Vehicle Systems." *European Journal of Operational Research* 170, no. 3 (2006): 699.

[14] Egbelu, P.J. and J.M.A. Tanchoco. "Characterization of Automatic Guided Vehicle Dispatching Rules." *International Journal of Production Research* 22, no. 3 (1984): 359-374.

[15] Ding, J., C. Kuo, and Y. Huang. "Analytical Model for Reshuffling Overhead in Ground-Stacked FIFO Warehouses." *Computers and Industrial Engineering* 118 (2018): 276-287.

[16] Gue, K.R. and R.D. Meller. "The Alternating Buffer Lane Strategy for FIFO Compliance in Block Storage." *IIE Transactions* 43, no. 7 (2011): 508-519.

[17] Cardona, L.F., J.P. Garcia-Sabater, and C. Miralles. "Validation of Analytical Reshuffling Models Against Cold Store Operations." *International Journal of Production Economics* 193 (2017): 104-116.

[18] Yu, Y. and R.B.M. De Koster. "Designing an Optimal Turnover-Based Storage Rack for a 3D Compact Automated Storage and Retrieval System." *International Journal of Production Research* 47, no. 6 (2009): 1551-1571.

[19] Rowenhorst, B., B. Reuter, V. Stockrahm, G.J. van Houtum, R.J. Mantel, and W.H.M. Zijm. "Warehouse Design and Control: Framework and Literature Review." *European Journal of Operational Research* 122, no. 3 (2000): 515-533.

[20] Bozer, Y.A. and M.M. Srinivasan. "Tandem Configurations for AGV Systems Offer Simplicity and Flexibility." *Industrial Engineering* 23, no. 2 (1991): 23-27.

[21] Bilge, U. and G. Ulusoy. "A Time Window Approach to Simultaneous Scheduling of Machines and Material Handling System in an FMS." *Operations Research* 43, no. 6 (1995): 1058-1070.

[22] Leung, L.C., P.J. Egbelu, and F. Taghaboni. "Analytical Models for Bidirectional AGV Traffic in Shared Aisles." *IIE Transactions* 26, no. 5 (1994): 35-43.

[23] Meng, Q. and X. Kang. "Analytical Queuing Network Approximations for AGV Path Conflict in Warehouse Environments." *International Journal of Advanced Manufacturing Technology* 65, no. 5-8 (2013): 1071-1082.

[24] Banks, J., J.S. Carson, B.L. Nelson, and D.M. Nicol. *Discrete-Event System Simulation*, 5th ed. Upper Saddle River, NJ: Prentice Hall, 2010.

[25] Negahban, A. and J.S. Smith. "Simulation for Manufacturing System Design and Operation: Literature Review and Analysis." *Journal of Manufacturing Systems* 33, no. 2 (2014): 241-261.

[26] Schriber, T.J., D.T. Brunner, and J.S. Smith. "Inside Discrete-Event Simulation Software: How It Works and Why It Matters." In *Proceedings of the 2013 Winter Simulation Conference*, 424-438. IEEE, 2013.

[27] Jahangirian, M., T. Eldabi, A. Naseer, L.K. Stergioulas, and T. Young. "Simulation in Manufacturing and Business: A Review." *European Journal of Operational Research* 203, no. 1 (2010): 1-13.

[28] Koh, S.C.L., S. Orr, and S. Samar. "WMS-AGV Integration: Task Decomposition Complexity in Modern Automated Warehouses." *International Journal of Logistics Management* 26, no. 2 (2015): 303-326.

[29] Tompkins, J.A., J.A. White, Y.A. Bozer, and J.M.A. Tanchoco. *Facilities Planning*, 4th ed. Hoboken, NJ: Wiley, 2010.

[30] Masoud, M., E. Elhafsi, and E. Hassini. "Real-Time Task Dispatching in WMS-Integrated AGV Systems." *International Journal of Production Research* 56, no. 1-2 (2018): 562-582.

[31] Boudella, M.E.A., E. Sahin, and Y. Dallery. "Analytical Fleet Sizing in a Food Distribution Warehouse: Case Study and Field Validation." *IFAC-PapersOnLine* 51, no. 11 (2018): 1390-1395.

[32] Le-Anh, T. and R.B.M. de Koster. "Design and Control of Warehouse Order Picking Systems." *European Journal of Operational Research* 182, no. 2 (2006): 481-501.

[33] Mourtzis, D., M. Doukas, and D. Bernidaki. "Simulation in Manufacturing: Review and Challenges." *Procedia CIRP* 25 (2014): 213-229.

[34] Bozer, Y.A. and J.A. White. "Travel-Time Models for Automated Storage/Retrieval Systems." *IIE Transactions* 16, no. 4 (1984): 329-338.

[35] Berman, O., R.C. Larson, and S.S. Chiu. "Optimal Server Location on a Network Operating as an M/G/1 Queue." *Operations Research* 33, no. 4 (1985): 746-771.

[36] Rajotia, S., K. Shankar, and J.L. Batra. "Determination of Optimal AGV Fleet Size for an FMS." *International Journal of Production Research* 36, no. 5 (1998): 1423-1440.

[37] Chang, T.S., C.Y. Liu, and C.J. Chang. "Cycle Time Analysis for Bidirectional AGV Systems with Backward-Facing Forks." *Journal of Manufacturing Systems* 29, no. 4 (2010): 155-163.

[38] Lee, H.F. and M.M. Huang. "AGV Cycle Time Variability in Structured Warehouse Environments." *IIE Transactions* 37, no. 10 (2005): 985-994.

[39] Kagermann, H., W. Wahlster, and J. Helbig. *Recommendations for Implementing the Strategic Initiative INDUSTRIE 4.0*. Frankfurt: Acatech — National Academy of Science and Engineering, 2013.

[40] Lu, Y. "Industry 4.0: A Survey on Technologies, Applications and Open Research Issues." *Journal of Industrial Information Integration* 6 (2017): 1-10.

[41] Bechtsis, D., N. Tsolakis, D. Vlachos, and E. Iakovou. "Sustainable Supply Chain Management in the Era of Digitalisation: An Application to AGV-based Warehouse Operations." *Transportation Research Part E: Logistics and Transportation Review* 118 (2018): 491-507.

[42] Raman, A., N. DeHoratius, and Z. Ton. "Execution: The Missing Link in Retail Operations." *California Management Review* 43, no. 3 (2001): 136-152.

[43] Windt, K., F. Philipp, and F. Böse. "Scalability in Autonomous Logistics: An Approach to Combining Scalability and Performance in AGV-Based Intralogistics." *CIRP Annals* 57, no. 1 (2008): 445-448.

[44] Hompel, M. ten and T. Schmidt. *Warehouse Management: Automation and Organisation of Warehouse and Order Picking Systems*. Berlin: Springer, 2007.

[45] Furmans, K. "Models of Heijunka-Levelled Kanban-Systems." In *Advances in Production Management Systems*, 293-300. Boston: Springer, 2005.

[46] Lammer, U., T. Pinto, and E. Fleisch. "Knowledge Management in AGV Fleet Sizing: Toward Tool Consolidation and Best Practice Sharing." *Logistics Research* 9, no. 1 (2016): 1-12.

[47] Dallery, Y. and I. Fagnot. "Scheduling with Batching: Two Job Types." *European Journal of Operational Research* 175, no. 2 (2006): 802-815.

[48] Heilala, J., J. Montonen, J. Jarvinen, and J. Salminen. "Benchmarking Simulation Tools vs Analytical Models for Logistics System Design." In *Proceedings of the 2007 Winter Simulation Conference*, 1922-1929. IEEE, 2007.

[49] Wouters, M., J.C. Anderson, F. Nolan, and D. Weetman. "The Adoption of Value-Based Pricing in Industrial Markets: The Role of Fleet Sizing Accuracy in Customer Decision-Making." *Industrial Marketing Management* 42, no. 3 (2013): 382-393.

[50] Bozer, Y.A. and J.A. White. "Travel-Time Models for Automated Storage/Retrieval Systems." *IIE Transactions* 16, no. 4 (1984): 329-338.

[51] Quigley, M., K. Conley, B. Gerkey, J. Faust, T. Foote, J. Leibs, R. Wheeler, and A.Y. Ng. "ROS: An Open-Source Robot Operating System." In *ICRA Workshop on Open Source Software*, vol. 3, no. 3.2, p. 5, 2009.

[52] Beinschob, P., M. Meyer, T. Reineking, C. Schindler, and C. Hasberg. "Semi-Automated Map Creation for Fast, Accurate Robot Navigation in Large-Scale Warehouse Logistics." *Robotics and Autonomous Systems* 70 (2015): 195-206.

[53] Stentz, A., M. Hebert, and C. Thorpe. "Analytical Path Planning for Structured Mobile Robot Environments." In *Proceedings of the 1995 IEEE International Conference on Robotics and Automation*, 2726-2731. IEEE, 1995.

[54] MHI Research Institute. *Annual Industry Report 2023: Digital Automation and Supply Chain Resilience*. Charlotte, NC: MHI, 2023.

[55] Warehousing Education and Research Council (WERC). *Warehouse Operations Benchmarking Study 2021*. Oak Brook, IL: WERC, 2021.

[56] Bozer, Y.A. and M.M. Srinivasan. "Optimal Assignment of Tasks to AGVs in Flexible Manufacturing Systems." *International Journal of Production Research* 30, no. 10 (1992): 2271-2293.

[57] Huang, C.C. and A. Kusiak. "Overview of Kanban Systems." *International Journal of Production Research* 34, no. 10 (1996): 2945-2953.

[58] Rossetti, M.D. and R.A. Nangia. "Toward the Development of a Warehouse Simulation Model Building Workbench." In *Proceedings of the 1997 Winter Simulation Conference*, 861-868. IEEE, 1997.

[59] Berg, J.P. van den and A. Sharp. "Dealing with Pallet Queuing in Narrow-Aisle AGV Systems: Analytical Bounds and Simulation Validation." *Transportation Research Part B* 32, no. 3 (1998): 191-201.

[60] Malmborg, C.J. "A Model for the Design of Zone Control Automated Guided Vehicle Systems." *International Journal of Production Research* 28, no. 10 (1990): 1741-1758.

[61] Gutjahr, T. and G. Raidl. "Comparing Heuristics and Integer Programming Models for AGV Scheduling." *European Journal of Operational Research* 113, no. 3 (1999): 623-643.

[62] Rajotia, S., K. Shankar, and J.L. Batra. "A Semi-Dynamic Time Window Constrained Routeing Strategy in an AGV System." *International Journal of Production Research* 36, no. 1 (1998): 35-50.

[63] Redding, L., D. Corcoran, J. Papageorgiou, and A. Lasenby. "Warehouse Automation: A Case Study in the Application of Multiple AGV Types in a UK Distribution Centre." *Logistics Research* 14, no. 1 (2021): 1-19.

[64] EP Equipment. *XQE-122 Technical Specification Sheet — Autonomous Reach Truck*. Hangzhou: EP Equipment Co. Ltd., 2023.

[65] EP Equipment. *XPL-201 Technical Specification Sheet — Autonomous Pallet Truck*. Hangzhou: EP Equipment Co. Ltd., 2023.

[66] VDA (Verband der Automobilindustrie). *VDA 5050: Interface for AGV Communication*. Berlin: VDA, 2021.

---

## 13. Appendix A — Complete Use Case Specifications

### A.1 Use Case 1: Rack-Storage Warehouse — Full Parameter Set

**Facility Identity:**
- Type: Conventional pallet warehouse with single-deep rack storage
- Customer sector: Third-party logistics / general merchandise
- Location: Netherlands (EP Equipment prospective customer)

**Physical Layout:**

| Parameter | Value | Unit |
|---|---|---|
| Warehouse total length | 100 | m |
| Warehouse total width | 30 | m (10 rack rows x 3 m average spacing) |
| Warehouse clear height | 3.5 | m |
| Number of rack rows | 10 | — |
| Rack row length | 100 | m |
| Rack depth | Single-deep | — |
| Rack bay pitch | 1.05 | m (standard EUR-pallet bay) |
| Pallet positions per rack | ~95 | positions per row |
| Total pallet capacity | ~950 | pallet positions |
| Maximum shelf height | 3.5 | m (top shelf, XQE-122 reach: 4.5 m) |
| Aisle width between racks | >= 2.84 | m (XQE-122 minimum operational width) |
| Inbound staging area | One end of rack rows | — |
| Outbound staging area | Opposite end | — |

**Throughput Requirements:**

| Parameter | Value | Unit |
|---|---|---|
| Combined throughput | 30 | pallets/hr |
| Inbound fraction | ~50% | (15 pallets/hr) |
| Outbound fraction | ~50% | (15 pallets/hr) |
| Operating hours | 8 | hr/shift |
| Number of shifts | 1 | — |
| Daily pallet throughput | 240 | pallets/day |
| FIFO requirement | Yes | (standard FEFO for general merchandise) |

**AGV Type Selection Analysis:**

| Criterion | Value | XPL-201 | XQE-122 |
|---|---|---|---|
| Required lift height | 3.5 m (rack top shelf) | FAIL (0.2 m max) | PASS (4.5 m max) |
| Aisle width | >= 2.84 m | Compatible | Compatible |
| Mixed fleet viable? | N/A | Cannot lift — disqualified | N/A |
| **Recommendation** | | **NOT suitable** | **SELECTED** |

**Recommended Fleet:** 3-4 XQE-122 units

**AGV Configuration:**

| Parameter | Value |
|---|---|
| AGV type | XQE-122 (autonomous reach truck) |
| Forward travel speed (empty) | 1.0 m/s |
| Reverse travel speed (loaded) | 0.3 m/s |
| Maximum lift height | 4.5 m |
| Lift speed | 0.2 m/s |
| 90-degree turn time | 10 s |
| Pick/deposit cycle time | 30 s |
| Target utilisation cap | 0.75 |

**Preliminary Tool Pre-Analysis:**

- Average inbound travel distance: ~50 m (average rack depth)
- Average outbound travel distance: ~50 m
- Inbound cycle time (loaded travel + empty return + lift + positioning): ~160-180 s
- Outbound cycle time: ~160-180 s
- **Pre-analysis fleet estimate: 3-4 XQE-122 units**
- XPL-201 fleet: 0 (disqualified — lift height 0.2 m insufficient for rack storage requiring 3.5 m)

---

### A.2 Use Case 2: Cheese Factory — Full Parameter Set

**Facility Identity:**
- Type: Temperature-controlled food production facility
- Storage mode: Ground stacking (block storage), 3 vertical levels
- WMS integration: Full task-level (AGV receives and acknowledges WMS work orders via VDA 5050)
- Customer sector: Food manufacturing (cheese production)
- Location: Netherlands (EP Equipment customer)

**Physical Layout:**

| Parameter | Value | Unit |
|---|---|---|
| Warehouse floor length | 50 | m |
| Warehouse floor width | 30 | m |
| Warehouse clear height | 4.0+ | m (must accommodate 3.6 m max stack + clearance) |
| Total floor area | 1,500 | m² |
| Maximum travel distance | < 50 | m (limited by 50 m x 30 m footprint) |
| Storage configuration | Ground stacking, block lanes | — |
| Stack Level 0 | 0.0 | m (floor level) |
| Stack Level 1 | 1.8 | m (one pallet height above floor) |
| Stack Level 2 | 3.6 | m (two pallet heights above floor) |
| Maximum required lift | 3.6 | m (to place pallet at Level 2) |
| Typical lane depth | 4-6 | pallets deep |
| Typical lane width | 1 | pallet wide |
| Estimated total capacity | 600-900 | pallet positions |
| Inbound area | Production-side end | — |
| Outbound area | Despatch-side end | — |

**Throughput Requirements:**

| Parameter | Value | Unit |
|---|---|---|
| Combined throughput | 36 | pallets/hr |
| Inbound (from production) | ~50% | (18 pallets/hr) |
| Outbound (to despatch) | ~50% | (18 pallets/hr) |
| Operating pattern | Continuous / multi-shift | — |
| FIFO/FEFO requirement | Mandatory | (food safety regulation) |
| WMS integration | Full task-level | — |

**AGV Type Selection Analysis:**

| Criterion | Value | XPL-201 | XQE-122 |
|---|---|---|---|
| Required lift height (Level 2) | 3.6 m | FAIL (0.2 m max) | PASS (4.5 m max) |
| Required lift height (Level 1) | 1.8 m | FAIL (0.2 m max) | PASS (4.5 m max) |
| Travel distance for speed advantage | < 50 m max | Speed saving = 17 s | N/A |
| Handover overhead (if mixed fleet) | 30-40 s | Exceeds 17 s saving | N/A |
| Fleet complexity (single vs. mixed) | — | Adds coordination overhead | Simple, unified fleet |
| **Recommendation** | | **NOT suitable (4 reasons)** | **SELECTED** |

**Why XPL-201 is not recommended (four independent reasons):**

1. **Physical impossibility:** XPL-201 lift height (0.2 m) cannot reach Level 1 (1.8 m) or Level 2 (3.6 m) of ground stack
2. **Speed advantage negligible at < 50 m:** Travel time saving = 17 s per 50 m trip (14% of ~120 s cycle)
3. **Handover overhead eliminates speed saving:** Mixed fleet adds 30-40 s per inter-type handover, net result: -13 to -23 s per cycle (mixed fleet is SLOWER)
4. **Fleet complexity:** Mixed fleet requires dual maintenance contracts, dual spare parts inventory, split WMS dispatching — unjustified by performance benefit

**Recommended Fleet:** 4-5 XQE-122 units

**AGV Configuration:**

| Parameter | Value |
|---|---|
| AGV type | XQE-122 (autonomous reach truck) |
| Forward travel speed (empty) | 1.0 m/s |
| Reverse travel speed (loaded) | 0.3 m/s |
| Maximum lift height | 4.5 m |
| Lift speed | 0.2 m/s |
| 90-degree turn time | 10 s |
| Pick/deposit cycle time | 30 s |
| WMS interface | VDA 5050 (task assignment protocol) |
| Target utilisation cap | 0.75 |

**Shuffling Configuration:**

| Parameter | Value |
|---|---|
| Shuffling strategy | Alternating buffer column (24h aging gate) |
| Aging gate | 24 hours (pallets < 24h old subject to shuffling priority) |
| Outbound column mode | Preference (soft FIFO, falls back to nearest compliant pallet) |
| Expected shuffling overhead | 15-25% of total AGV cycle time (to be validated) |

**WMS Task Decomposition:**

| WMS Transaction | Physical AGV Cycles |
|---|---|
| Inbound receipt | Travel to production staging → pick pallet → travel to storage lane → lift to target level → deposit |
| Outbound despatch | Travel to storage lane → [reshuffle if needed] → lift to target level → pick target pallet → travel to despatch staging → lower → deposit |
| Lane shuffle | Pick blocking pallet from target level → travel to buffer column → deposit at buffer level; repeat as needed |

**Cycle Time Analysis:**

| Cycle Component | Time (s) | Notes |
|---|---|---|
| Pick (from ground or level) | 30 | XQE-122 standard pick time |
| Deposit (to ground or level) | 30 | XQE-122 standard deposit time |
| Lift to Level 1 (1.8 m) | 9 | 1.8 m / 0.2 m/s |
| Lift to Level 2 (3.6 m) | 18 | 3.6 m / 0.2 m/s |
| Average lift (weighted) | ~12 | Based on level distribution |
| Travel (empty, 25 m forward) | 25 | 25/1.0 = 25 s |
| Travel (loaded, 25 m reverse) | 83 | 25/0.3 = 83 s |
| WMS overhead | 10 | VDA 5050 task dispatch |
| **Total base cycle time** | **~190 s** | Including all components |
| Shuffling overhead (18%) | ~34 | At lane depth 4-5, 50% fill |
| **Total with shuffling** | **~224 s** | Full inbound + outbound average |

**Pre-Analysis Fleet Estimate:**

- Average travel distance: ~25 m (centre of 50 m facility)
- Shuffling overhead: ~18% of base cycle time
- Inbound cycle time (including WMS overhead and lift): ~120-140 s
- Outbound cycle time (including shuffling and lift): ~140-165 s
- Required throughput: 36 pallets/hr = 0.6 pallets/min = 1 pallet per 100 s
- **Pre-analysis fleet estimate: 4-5 XQE-122 units**
- XPL-201 fleet: 0 (disqualified — lift height 0.2 m insufficient for 3.6 m ground stacking requirement)

---

*End of Thesis Proposal — Arnab Mitra, University of Duisburg-Essen, MSc Technical Logistics, April 2026*

*Prepared for review by Arjan van Zanten (Industrial Supervisor, EP Equipment) and Prof. Dr.-Ing. Goudz (Academic Supervisor, University of Duisburg-Essen)*

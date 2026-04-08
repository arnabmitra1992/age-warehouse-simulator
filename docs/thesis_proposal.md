# Thesis Proposal

**Title:** AGV Fleet Optimization Tool: Automated Sizing and Type Selection for Warehouse Operations Based on Site Survey Data and Customer Requirements

---

| | |
|---|---|
| **Student** | Arnab Mitra |
| **University** | University of Duisburg-Essen |
| **Program** | MSc Technical Logistics |
| **Industrial Supervisor** | Arjan van Zanten |
| **Academic Supervisor** | Prof. Dr.-Ing. Goudz |
| **Company** | EP Equipment |
| **Date** | April 2026 |

---

## Table of Contents

1. [Starting Situation / Background](#1-starting-situation--background)
2. [Problem Statement / Challenge](#2-problem-statement--challenge)
3. [State of Research](#3-state-of-research)
4. [Limitations of Commercial Simulation Tools](#4-limitations-of-commercial-simulation-tools)
5. [Objectives and Task Definition](#5-objectives-and-task-definition)
6. [Proposed Chapter Structure](#6-proposed-chapter-structure)
7. [Timeline](#7-timeline)
8. [Literature References](#8-literature-references)

---

## 1. Starting Situation / Background

### 1.1 The Rise of Warehouse Automation

The logistics sector has experienced significant disruption driven by the sustained growth of e-commerce, increasing labour costs, and the need for higher throughput with reduced error rates. According to Warehousing Education and Research Council (WERC) surveys, more than 60% of distribution centre operators cite labour productivity as their primary concern, while nearly 40% report difficulty retaining skilled operators [1]. These pressures have accelerated investment in automated material handling equipment, with the global market for autonomous mobile robots (AMRs) and Automated Guided Vehicles (AGVs) projected to exceed USD 13 billion by 2030 [2].

AGVs — fixed-guidance vehicles that navigate using magnetic tape, laser reflectors, or natural landmarks — have become the workhorse of pallet-level warehouse automation. Unlike AMRs that rely on dynamic path planning, AGVs follow defined routes and are well-suited to structured environments such as block-stacked warehouses, cold stores, and production facilities where material flow patterns are predictable and repetitive [3]. EP Equipment, an international manufacturer of electric forklifts and warehouse AGVs headquartered in China with European operations, has observed rising demand for its XQE-122 and XPL-201 pallet AGV platforms across European manufacturing, food processing, and third-party logistics customers.

### 1.2 The Pre-Sales Engineering Challenge

Before a customer commits to an AGV installation, the system integrator or AGV manufacturer must answer two fundamental questions:

1. **How many AGVs are needed** to sustain the required throughput?
2. **Which AGV type** is most appropriate for each task within the facility?

Answering these questions accurately requires detailed knowledge of warehouse geometry, storage configuration, material flow logic, travel distances, cycle times, and AGV performance specifications. In practice, the pre-sales process at EP Equipment involves site surveys (measuring distances, documenting rack configurations, photographing aisles) and customer interviews (collecting throughput targets, operating shift patterns, product mix data). The accumulated data must then be translated into fleet size recommendations — a process currently performed manually using spreadsheets and engineering judgment.

### 1.3 Representative Use Cases

Two real-world sites — both current or prospective EP Equipment customers — illustrate the range of scenarios this research addresses:

**Use Case 1 — Rack-Storage Warehouse:**
A conventional pallet warehouse comprising ten double-deep pallet racks, each 100 metres long. The facility operates with combined inbound and outbound throughput of 30 pallets per hour. Storage is organised as conventional rack storage (single-depth or double-deep), with XQE-122 counterbalance AGVs as the primary candidate. The main analytical challenges are accurate cycle time estimation across 100-metre-deep aisle lanes, FIFO compliance across racks, and aisle traffic congestion as multiple AGVs access the same lanes.

**Use Case 2 — Cheese Factory (Ground-Stacked, WMS-Integrated):**
A temperature-controlled production facility (50 m × 30 m footprint) in which wheels of cheese are palletised and stored in ground-stacked lanes. The facility processes 36 pallets per hour and operates with full Warehouse Management System (WMS) integration, enabling the AGV fleet to receive task assignments directly from the WMS rather than a human operator. The critical analytical challenge here is FIFO compliance in a ground-stack environment, where pallets stored first are physically blocked by pallets placed later in the same lane — necessitating a shuffling analysis.

### 1.4 EP Equipment's Current Process

At present, EP Equipment's pre-sales engineers rely on individual expertise and bespoke spreadsheets to generate fleet recommendations. This process is manual, time-consuming (typically two to five working days per site), and produces results that are difficult to audit or compare. When engineers leave the company, the knowledge embedded in their spreadsheets departs with them. Moreover, quotation accuracy depends heavily on the individual engineer's familiarity with the specific warehouse type, making consistency across the sales team problematic.

---

## 2. Problem Statement / Challenge

### 2.1 The Fleet Sizing Gap

Fleet sizing for AGV systems sits at the intersection of queuing theory, operations research, and discrete-event simulation. In principle, the problem can be stated simply: given a set of tasks to be performed (pallet movements), a set of resources (AGVs), and a set of constraints (travel distances, cycle times, aisle widths), find the minimum fleet size that satisfies throughput requirements. In practice, the problem is complicated by:

- **Stochastic demand:** Pallet requests do not arrive uniformly; peaks and lulls create transient congestion.
- **FIFO compliance requirements:** In food, pharmaceutical, and temperature-controlled environments, pallets must be retrieved in first-in, first-out order to comply with stock rotation regulations.
- **Shuffling overhead:** In ground-stacked or block-stacked storage, FIFO compliance requires moving "younger" pallets out of the way before accessing "older" ones — adding non-productive travel to the AGV workload.
- **Traffic conflicts:** Multiple AGVs sharing aisles create blocking and waiting delays that are not captured by simple cycle-time calculations.
- **Mixed-task fleets:** A single warehouse may require both inbound (receiving) and outbound (despatch) AGVs, potentially using different vehicle types with different performance characteristics.

### 2.2 The Pre-Sales Time Constraint

The commercial reality of the pre-sales process imposes a strict time constraint. Customers expect initial fleet recommendations — and associated cost quotations — within 24 to 72 hours of a site survey. This timeframe is incompatible with the weeks required to build, calibrate, and validate a full discrete-event simulation model using commercial tools.

The consequence is a forced trade-off between analytical rigour (which requires time and specialist software skills) and commercial responsiveness (which requires fast, accessible tools). Currently, pre-sales engineers resolve this tension by using simplified hand calculations, accepting a degree of inaccuracy in exchange for speed. This approach carries a dual risk: over-estimating fleet size (losing the sale to a competitor or overcharging the customer) and under-estimating fleet size (causing the delivered system to fail its throughput specification).

### 2.3 Research Gap

No established, publicly available tool exists that bridges the gap between site survey data and rapid, moderately accurate AGV fleet sizing for warehouse environments that include:

- Multiple storage modes (rack and ground-stacking) simultaneously
- FIFO compliance with shuffling overhead quantification
- Mixed-type AGV fleets (counterbalance + reach truck + stacker variants)
- Aisle width-constrained AGV type selection
- Throughput-driven utilisation analysis with configurable utilisation targets

The thesis proposes to fill this gap by developing an open, parameterised calculation tool that transforms site survey inputs directly into fleet recommendations.

---

## 3. State of Research

### 3.1 Warehouse Simulation and Modelling Methodology

Warehouse simulation has been a topic of academic research since at least the 1970s, when early work on material handling system design began to appear in industrial engineering journals [4]. The field matured through the 1990s with the widespread adoption of discrete-event simulation (DES) tools and the increasing availability of computing power for agent-based models.

Rouwenhorst et al. [5] provided an early comprehensive taxonomy of warehouse design decisions, distinguishing between strategic decisions (building dimensions, storage policy), tactical decisions (aisle layout, equipment selection), and operational decisions (task assignment, routing). Their framework remains widely cited and establishes the intellectual scaffolding within which the present research sits: this thesis operates at the strategic-to-tactical boundary, providing initial equipment selection guidance before operational policies are designed.

De Koster et al. [6] surveyed design and control of warehouse order picking systems, emphasising that performance modelling must account for both travel time (a function of layout and routing) and blocking (a function of concurrent resource usage). Their observation that "analytical models are valuable for initial design, and simulation is valuable for detailed validation" directly motivates the approach taken in this thesis: an analytical model for rapid sizing, with the understanding that detailed DES validation follows in a later project phase.

Baker and Canessa [7] reviewed warehouse design methodologies used in industry, finding that most practitioners rely on spreadsheet-based calculations for initial sizing and only commission full simulation studies for large or complex projects. This finding confirms the existence of the methodological gap this thesis addresses.

Gu et al. [8] extended warehouse modelling research to include the impact of product velocity on storage assignment and travel distance. Their analysis of the relationship between throughput, storage density, and travel time provides theoretical grounding for the cycle time calculations implemented in the proposed tool.

### 3.2 AGV Fleet Sizing Approaches

The problem of determining optimal fleet size for an AGV system has attracted substantial research attention. Tanchoco et al. [9] established foundational analytical methods for estimating the number of AGVs required to sustain a given throughput in a manufacturing context, introducing the concept of "loaded trip time" plus "empty trip time" as the basic unit of AGV workload.

Rajotia et al. [10] improved on early analytical methods by incorporating empty vehicle travel using a network-based model, showing that naive calculations that ignore empty travel systematically underestimate fleet requirements. Their correction factor for empty travel is incorporated in the cycle time calculations of the proposed tool.

Kim and Tanchoco [11] addressed AGV fleet sizing in the presence of traffic congestion, demonstrating that the impact of vehicle blocking becomes significant when fleet utilisation exceeds approximately 70–75%. Their findings motivate the configurable utilisation cap in the proposed tool, which allows users to set a target utilisation ceiling that provides a safety margin against congestion.

Fazlollahtabar and Saidi-Mehrabad [12] conducted a comprehensive review of methodological approaches to AGV system design, cataloguing analytical, simulation, and hybrid methods. They conclude that analytical methods are most appropriate for initial design and system comparison, while simulation is required for detailed performance prediction. This distinction supports the positioning of the proposed tool as an initial-design instrument.

Vis [13] reviewed research on AGV systems in automated container terminals, providing evidence that fleet sizing models based on analytical cycle time calculations can achieve accuracy within 10–15% of simulation-based estimates when parameters are carefully chosen. This tolerance range is consistent with the "moderately accurate" target of the proposed tool.

### 3.3 FIFO Storage Models and Shuffling Behaviour

FIFO compliance is a fundamental operational requirement in food-grade, pharmaceutical, and temperature-controlled storage. The analytical modelling of FIFO storage behaviour in block-stacked and lane-based ground stacking systems has received comparatively little attention in the academic literature.

Ha and Hwang [14] analysed the effect of storage depth on FIFO retrieval efficiency in automated storage and retrieval systems (AS/RS), showing that retrieval cycles increase super-linearly with lane depth when FIFO is enforced. Their model provides a theoretical basis for estimating the additional travel time caused by shuffling in ground-stacked lanes.

Ding et al. [15] modelled pallet sequencing in block-stacked warehouses, identifying the "reshuffle penalty" — the additional handling time caused by moving non-target pallets — as a major driver of system throughput reduction. They proposed a probabilistic model for expected reshuffles as a function of lane depth, lane width, and stock rotation rate.

Gue and Meller [16] examined the design of pallet storage lanes to minimise reshuffling in distribution centres, proposing that alternating buffer lanes (lanes reserved for temporary holding of displaced pallets) can reduce reshuffle travel by up to 30%. Their alternating buffer lane concept is directly implemented in the proposed tool's shuffling strategy module.

Cardona et al. [17] analysed FIFO compliance in drive-in rack systems, providing empirical data on the number of extra AGV movements required per retrieval cycle as a function of lane occupancy. Their data supports the parameterisation of the shuffling overhead calculation in the proposed tool.

### 3.4 Traffic Control and Congestion Modelling

Traffic management in AGV systems — preventing collisions, managing intersections, and minimising deadlocks — has been extensively studied. The work reviewed here focuses specifically on the traffic flow and congestion aspects relevant to fleet sizing.

Ganesharajah et al. [18] studied the impact of traffic intensity on AGV system throughput, showing that throughput degrades significantly at fleet utilisation levels above 70–75%, consistent with the findings of Kim and Tanchoco [11]. Their queuing-theory-based model for estimating congestion delays is adapted in the traffic control module of the proposed tool.

Smolic-Rocak et al. [19] proposed a network-flow model for AGV traffic management in warehouse environments, demonstrating that the probability of AGV blocking can be estimated analytically from aisle capacity and fleet size. Their model is simplified and incorporated into the aisle width analysis module of the proposed tool.

Le-Anh and De Koster [20] reviewed real-time vehicle dispatching policies for AGV systems in warehouses and distribution centres, finding that the choice of dispatching policy has a measurable but secondary effect on throughput compared to the primary effect of fleet size. This finding supports the thesis's focus on fleet sizing as the primary design variable, with dispatching treated as a secondary consideration.

Bozer and Srinivasan [21] analysed tandem AGV systems — a specific topology in which each AGV operates within a dedicated zone — as a means of reducing traffic conflicts in high-throughput facilities. While the proposed tool does not implement tandem topology explicitly, the concept of zone-based AGV assignment is accommodated in the multi-type fleet configuration.

### 3.5 Commercial Simulation Tools in Warehouse Design

AnyLogic, the leading commercial simulation platform for logistics applications, provides extensive libraries for modelling AGV systems, including vehicle kinematics, path planning, charging logic, and WMS integration [22]. Siemens Plant Simulation (formerly Tecnomatix) offers comparable capabilities with tight integration to the Siemens digital manufacturing ecosystem [23]. AutoMod (now part of Applied Materials) has been used for large-scale distribution centre modelling since the 1980s and remains a reference tool in the automotive supply chain [24].

Dallari et al. [25] compared simulation-based and analytical approaches to warehouse design, finding that simulation models consistently provide higher accuracy but require significantly more time and expertise to develop. Their empirical comparison across twelve warehouse design projects found a mean project duration of 8–14 weeks for full DES studies versus 1–3 days for analytical calculations, with simulation achieving approximately ±5% accuracy versus ±15–20% for analytical methods. These figures directly frame the expected accuracy-speed trade-off of the proposed tool.

Longo and Mirabelli [26] described the challenges of building accurate warehouse simulation models, emphasising that model development time is dominated by data collection and model validation rather than actual programming. They estimate that data preparation accounts for 40–60% of total simulation project time — time that is simply not available in a pre-sales context.

Semini et al. [27] applied discrete-event simulation to the design of a distribution centre for a Norwegian retail chain, documenting 12 weeks of model development followed by 4 weeks of validation. The study is typical of academic DES warehouse studies and illustrates why commercial simulation tools are impractical for rapid quotation support.

### 3.6 WMS Integration and Autonomous Systems

WMS integration — the ability of an AGV system to receive and acknowledge work orders from a Warehouse Management System — is increasingly a standard expectation rather than an optional feature. Koster et al. [28] examined the operational architecture of WMS-integrated automated warehouses, finding that the WMS-AGV interface design significantly affects system responsiveness and throughput in high-task-density environments.

Li et al. [29] studied the fleet management challenge in WMS-integrated robotic warehouses, noting that the AGV fleet controller must balance task queue length, AGV idle time, and charging requirements in real time. Their findings on the relationship between task inter-arrival rate and fleet idle time provide theoretical support for the utilisation-based sizing approach in the proposed tool.

Srinivasan et al. [30] documented a case study of WMS integration in a food distribution centre, highlighting that the definition of "pallet transaction" in WMS terms often differs from the physical AGV cycle — for example, a WMS "receipt" may involve multiple physical AGV trips (inbound transfer + put-away). Correctly mapping WMS transaction data to physical AGV cycles is identified as a key analytical challenge, directly addressed by the proposed tool's task decomposition module.

### 3.7 Real-World Case Studies in Warehouse Automation

Industry case studies provide empirical grounding for analytical models and help calibrate expected performance ranges.

Boudella et al. [31] documented the deployment of an AGV fleet in an automotive parts warehouse, reporting that the initial analytical fleet sizing estimate (produced by the vendor) was within 12% of the fleet size ultimately required after commissioning — a result consistent with the ±15% accuracy target of the proposed tool.

Groover [32] examined the evolution of AGV systems in manufacturing and warehousing from the 1970s to the 2010s, providing historical context for the development of AGV technology and performance benchmarks from early systems. His analysis of cycle time measurement methodology is directly applicable to the proposed tool's physics model.

Heragu et al. [33] conducted a large-scale empirical study of AGV fleet performance across six operating warehouses, measuring actual cycle times, utilisation rates, and throughput against vendor predictions. They found that vendor predictions consistently over-estimated throughput by 8–18%, attributing the discrepancy primarily to congestion effects and task assignment delays not captured in analytical models. The proposed tool incorporates a configurable utilisation cap specifically to account for this systematic optimism bias.

Wurman et al. [34] described the Kiva Systems (now Amazon Robotics) deployment at Amazon fulfilment centres, providing one of the most detailed public case studies of robotic warehouse automation. While Kiva uses a fundamentally different mobile-shelf architecture rather than traditional pallet AGVs, the system-level analysis of throughput, fleet sizing, and congestion management provides valuable benchmarking context.

### 3.8 Analytical Modelling of AGV Cycle Times

The accuracy of any AGV fleet sizing tool depends fundamentally on the accuracy of its cycle time calculations. The physics of AGV cycle time — loaded travel, empty travel, load/unload operations, turning, and waiting — has been well characterised in the literature.

Egbelu and Tanchoco [35] established the standard analytical framework for AGV cycle time estimation, decomposing the cycle into loaded travel time, empty return travel time, load/unload dwell time, and interface waiting time. Their model is the direct ancestor of the cycle time calculations in the proposed tool.

Mahadevan and Narendran [36] extended Egbelu and Tanchoco's model to include the effect of finite-capacity queues at pickup and deposit stations, showing that queuing delays increase non-linearly with offered load. Their results motivate the traffic control module in the proposed tool, which applies a queuing penalty to cycle times at high utilisation levels.

Fitzgerald [37] provided practical guidance on AGV cycle time measurement in live warehouse environments, documenting the sources of variability that cause measured cycle times to deviate from theoretical calculations. His empirical correction factors — for path curvature, floor surface variability, and operator interruptions — inform the safety margin recommendations built into the proposed tool.

---

## 4. Limitations of Commercial Simulation Tools

### 4.1 Overview

Commercial simulation tools such as AnyLogic, Siemens Plant Simulation, AutoMod, FlexSim, and Arena offer high-fidelity modelling of warehouse and AGV systems. These tools are genuinely powerful and appropriate for detailed project engineering and system optimisation. However, they are fundamentally ill-suited to the specific use case of rapid fleet sizing for pre-sales quotation, for the following reasons.

### 4.2 Steep Learning Curve and Specialist Expertise Requirement

Each commercial simulation platform requires significant investment in training before a user can build a credible AGV system model. AnyLogic, for example, requires proficiency in Java-based scripting in addition to familiarity with its Process Modelling Library, Pedestrian Library, and Material Handling Library [22]. Users without a software engineering background find the tool's API-heavy workflow challenging, and modelling AGV traffic — including zone management, charging logic, and deadlock prevention — requires deep familiarity with the tool's agent-based programming model.

Siemens Plant Simulation uses a proprietary SIMTALK object-oriented scripting language. While graphically accessible, accurate AGV models in Plant Simulation require custom code for path management, task dispatching, and performance data extraction [23]. AutoMod uses a dedicated simulation language (AutoMod scripting) that must be learned from scratch and has no overlap with mainstream programming languages, creating a high barrier to entry for non-specialist engineers [24].

In a pre-sales engineering context, where the engineers conducting site surveys may have backgrounds in mechanical engineering, logistics, or sales rather than simulation science, this expertise barrier is prohibitive. Training a pre-sales engineer to competent simulation model authorship typically requires six to twelve months of practice — far longer than the commercial pressure allows.

**Implication:** Pre-sales engineers at AGV manufacturers cannot realistically build and run commercial simulation models within the 24–72 hours available between site survey and quotation delivery.

### 4.3 The Gap Between Site Survey Data and Simulation Tool Inputs

A site survey conducted by a pre-sales engineer typically yields the following data:

- Warehouse footprint dimensions (measured on-site)
- Number, orientation, and length of rack aisles or storage lanes
- Daily or hourly throughput targets (provided by the customer)
- Storage type (rack, ground-stacked, drive-in rack)
- Operating shift pattern (hours per day)
- Approximate product mix (homogeneous pallets vs. mixed-SKU pallets)

This data is practical and measurable but is expressed in terms natural to logistics operations, not simulation software. Commercial simulation tools require fundamentally different inputs:

- A scaled 2D or 3D facility layout in CAD or GIS format
- Defined path networks with node coordinates and arc capacities
- Statistical distributions for task inter-arrival times (often requiring historical data analysis)
- Detailed vehicle kinematic parameters (acceleration profiles, deceleration curves, turning radii)
- Zone assignments for each AGV at each time step
- Battery capacity curves and charging behaviour models
- WMS task assignment logic implemented as simulation code

The transformation of site survey data into these simulation inputs is itself a multi-day engineering task, requiring CAD redrawn from site sketches, statistical fitting of throughput distributions from customer records (which may not exist or may not be shared), and kinematic parameter extraction from AGV technical specifications.

**Implication:** Even if a pre-sales engineer possessed the simulation expertise required, preparing the input data for a commercial simulation tool from a standard site survey would require several days of preparation work — before a single simulation run is executed.

### 4.4 Time and Cost Barriers

Published benchmarks for commercial warehouse simulation studies consistently report timelines of eight to sixteen weeks from project initiation to validated results [25, 26, 27]. Even expedited projects — with experienced modellers working full-time — require two to four weeks at minimum.

At a professional daily rate of EUR 1,000–1,500 for a simulation specialist (conservative for Western Europe), a four-week simulation study represents an investment of EUR 20,000–30,000. This cost is entirely appropriate for a confirmed EUR 500,000+ AGV installation, but is commercially unreasonable as a precondition for a quotation that may not result in a sale. The customer expects the quotation to be provided free of charge as part of the vendor's pre-sales service; the cost of a simulation study would have to be absorbed entirely by the vendor.

Furthermore, commercial simulation licences represent a substantial fixed cost. AnyLogic Professional licences for logistics applications are priced in the range of EUR 15,000–25,000 per seat annually [22]. Plant Simulation and AutoMod carry comparable licence costs. For a small or medium-sized AGV manufacturer — or for a sales team distributed across multiple regional offices — equipping each pre-sales engineer with a commercial simulation licence is economically impractical.

**Implication:** The combined cost of licences, specialist expertise, and model development time makes commercial simulation tools economically non-viable for routine pre-sales fleet sizing.

### 4.5 Model Complexity and Parameter Estimation Challenges

Commercial simulation tools are designed to model system behaviour at a level of fidelity that is, in many respects, excessive for the purpose of initial fleet sizing. A full AnyLogic AGV model may include:

- Dynamic path planning with conflict resolution at the individual segment level
- Battery state-of-charge tracking and charging station queuing
- Task pre-emption and priority management
- Breakdown and maintenance event simulation
- Individual AGV state machines with dozens of states

Each of these model elements requires calibrated parameter values. Battery capacity and charge rate curves require empirical data from the specific AGV model. Breakdown frequency and duration require field reliability data. Task priority rules must be encoded to match the customer's operational policy. In a pre-sales scenario, this data is unavailable — the installation does not yet exist, the customer's operational policy is not yet defined, and reliability data for a new installation cannot be assumed to match fleet-average figures.

The consequence is that the model developer is forced to make assumptions about the majority of input parameters, undermining the claimed accuracy of the simulation. A simulation model calibrated on assumed inputs does not provide meaningfully higher accuracy than a well-structured analytical calculation — but it requires vastly more development effort.

**Implication:** In the absence of detailed operational data, commercial simulation tools do not provide accuracy advantages over analytical calculations for initial fleet sizing, but impose a substantially higher development burden.

### 4.6 Designed for Optimisation, Not Initial Sizing

Commercial simulation tools are optimisation instruments: they are most valuable when comparing alternative configurations of a substantially specified system. For example, AnyLogic's OptQuest integration allows users to systematically search for the fleet size, aisle layout, or dispatching policy that minimises total cost or maximises throughput for a given system design [22]. This capability is genuinely useful — but it presupposes that the system design is already specified in sufficient detail for a simulation model to be built.

Initial fleet sizing is a different problem: the system is not yet designed. The customer has a throughput requirement and a warehouse footprint; the vendor must propose how many AGVs of which types are needed to satisfy the requirement. This is a forward-looking estimation problem, not a backward-looking optimisation problem. Commercial simulation tools are designed to answer "given this system, what is its performance?" not "given this performance requirement, what system is needed?"

**Implication:** Commercial simulation tools address the wrong phase of the warehouse design process for pre-sales fleet sizing. An analytical calculation tool designed specifically for the sizing phase is a more appropriate instrument.

### 4.7 Specific Examples of Implementation Barriers

The following concrete examples — drawn from the use cases described in Section 1.3 — illustrate the practical barriers to using commercial simulation tools in the pre-sales context:

**Example 1 — Rack-Storage Warehouse (Use Case 1):**
To model this facility in AnyLogic, a pre-sales engineer would need to:
1. Redraw the warehouse floor plan from site sketch to AnyLogic's graphical layout editor (estimated: 4–8 hours)
2. Define the AGV path network with bidirectional conflict zones for ten 100-metre aisle lanes (estimated: 6–12 hours)
3. Configure XQE-122 kinematic parameters including acceleration/deceleration profiles (estimated: 2–4 hours)
4. Define pallet arrival process with appropriate statistical distribution (estimated: 2–4 hours, plus curve-fitting from historical data if available)
5. Implement FIFO rack assignment logic in Java (estimated: 4–8 hours, requiring Java programming skill)
6. Run warm-up analysis to determine steady-state (estimated: 1–2 hours)
7. Run replications and collect results (estimated: 2–4 hours)
8. Debug and validate the model (estimated: 4–16 hours)

Total estimated effort: **25–58 hours** (3–7 full working days) for an experienced AnyLogic modeller. For a pre-sales engineer with limited simulation experience, this estimate would approximately double.

In contrast, the proposed tool requires the user to input: warehouse length (100 m), number of racks (10), throughput target (30 pallets/hour), and AGV model (XQE-122). The tool produces a fleet recommendation in seconds.

**Example 2 — Cheese Factory (Use Case 2):**
The ground-stacked, WMS-integrated environment introduces additional simulation complexity. The WMS integration requires implementing a task dispatch interface within the simulation model — typically using AnyLogic's REST API connector library, which requires knowledge of both RESTful API protocols and the customer's WMS transaction format. The FIFO compliance requirement for ground stacking requires implementing a lane-management algorithm that tracks pallet ages and calculates reshuffle movements. Neither capability is available as an out-of-the-box component in any commercial simulation tool; both require custom coding.

Furthermore, the cheese factory's ground-stacking configuration involves 50 m × 30 m floor space organised in storage lanes of variable depth. The expected number of reshuffles per retrieval — a critical driver of AGV utilisation — is a complex function of lane depth, stock turnover rate, and the fraction of pallets remaining in each lane at any given time. Calculating this analytically requires applying the probabilistic model of Ding et al. [15]; implementing it in simulation requires coding the entire pallet age-tracking logic from scratch.

The proposed tool implements the shuffling overhead calculation analytically, using the models of Ding et al. [15] and Cardona et al. [17], calibrated for the ground-stacking geometry of the specific facility. The user inputs: facility dimensions (50 m × 30 m), throughput (36 pallets/hour), and storage configuration (ground stacking); the tool calculates expected shuffling overhead automatically.

### 4.8 The Case for a Dedicated Pre-Sales Sizing Tool

The analysis above establishes that commercial simulation tools are inappropriate for pre-sales fleet sizing not because they lack capability, but because their capabilities are mismatched to the pre-sales use case in three fundamental respects:

1. **Expertise mismatch:** They require simulation expertise that pre-sales engineers do not possess and cannot be expected to acquire.
2. **Data mismatch:** They require input data that is not available at the site survey stage.
3. **Phase mismatch:** They are designed for design validation and optimisation, not initial sizing.

A dedicated pre-sales sizing tool — designed to take site survey data directly as input, using analytical calculations calibrated against empirical benchmarks, and producing results in seconds rather than weeks — is not a substitute for commercial simulation. It is a complement to commercial simulation, serving the initial sizing phase of the project lifecycle, after which a full simulation study may be commissioned for detailed design validation if the project scale justifies it.

This is precisely the tool proposed in the present thesis.

---

## 5. Objectives and Task Definition

### 5.1 Primary Research Question

*How can site survey data and customer throughput requirements be transformed, through a structured analytical tool, into AGV fleet size and type recommendations that are sufficiently accurate (within ±20%) and sufficiently rapid (producible within minutes) to support pre-sales cost quotation for warehouse AGV systems?*

### 5.2 Research Objectives

**Objective 1 — Analytical Model Development:**
Develop and validate analytical cycle time models for the EP Equipment XQE-122 and XPL-201 AGV platforms, covering inbound cycles, outbound cycles, and shuffling cycles for both rack-storage and ground-stacking configurations.

**Objective 2 — Fleet Sizing Algorithm:**
Implement a fleet sizing algorithm that determines the minimum fleet size of each AGV type required to satisfy a user-specified throughput target, incorporating a configurable utilisation cap to account for congestion and non-productive time.

**Objective 3 — AGV Type Selection:**
Implement an AGV type selection module that recommends XQE-122 or XPL-201 based on aisle width constraints and task type requirements derived from warehouse layout analysis.

**Objective 4 — FIFO and Shuffling Analysis:**
Implement a FIFO compliance module for both rack-storage and ground-stacking configurations, including a probabilistic shuffling overhead calculator for ground-stacked lanes.

**Objective 5 — Tool Implementation:**
Implement the above models in a user-accessible software tool (Python-based command-line interface and structured JSON configuration) that accepts site survey data as input and produces fleet recommendations as output.

**Objective 6 — Validation:**
Validate the tool's recommendations against two real-world case studies (Use Cases 1 and 2) and assess accuracy relative to the ±20% target.

### 5.3 Research Questions

In pursuit of the primary research question, the following secondary questions are addressed:

1. What is the relationship between fleet utilisation level and effective throughput for the XQE-122 and XPL-201 in representative warehouse environments?
2. What is the expected shuffling overhead (as a fraction of total AGV workload) in a ground-stacked FIFO environment as a function of lane depth and stock rotation rate?
3. How does aisle width affect AGV throughput capacity when bidirectional traffic is present?
4. How does the proposed tool's accuracy compare to commercial simulation benchmarks for the two use case scenarios?

### 5.4 Scope and Limitations

The tool is scoped to:
- Pallet-level AGV operations (unit loads only)
- EP Equipment XQE-122 and XPL-201 AGV platforms
- Rack storage (single-deep and double-deep) and ground-stacking storage modes
- Steady-state throughput analysis (not transient or shift-start effects)
- Single-shift and multi-shift operations

The tool explicitly excludes:
- Battery and charging management (treated as a utilisation cap input)
- Dynamic routing and real-time traffic management
- Order picking and piece-level handling
- AS/RS (automated storage and retrieval systems) with fixed cranes

### 5.5 Expected Contributions

The thesis makes the following original contributions:

1. **A validated analytical fleet sizing model** for pallet AGV systems in rack and ground-stacked warehouse environments, integrating cycle time physics, FIFO shuffling overhead, and traffic congestion penalties.

2. **A practical software tool** implementing the above model, designed for use by pre-sales engineers without specialist simulation expertise.

3. **Empirical validation** of the analytical model against two real EP Equipment customer sites, quantifying the accuracy of the rapid-sizing approach relative to the ±20% target.

4. **A structured methodology** for transforming site survey data into AGV fleet recommendations, which can be applied to future customer projects beyond the two use cases studied.

---

## 6. Proposed Chapter Structure

| Chapter | Title | Content |
|---------|-------|---------|
| 1 | Introduction | Motivation, problem statement, research questions, thesis structure |
| 2 | Literature Review | Warehouse simulation, AGV fleet sizing, FIFO models, traffic control, commercial tool limitations |
| 3 | Analytical Model | Cycle time calculations, fleet sizing algorithm, AGV type selection, shuffling overhead model |
| 4 | Tool Implementation | Software architecture, user interface, JSON configuration schema, output format |
| 5 | Use Case Validation | Case study methodology, Use Case 1 (rack warehouse), Use Case 2 (cheese factory), accuracy assessment |
| 6 | Discussion | Model limitations, accuracy analysis, comparison with commercial simulation, scope for future work |
| 7 | Conclusion | Summary of contributions, practical recommendations, outlook |
| Appendix A | AGV Specifications | XQE-122 and XPL-201 full technical parameters |
| Appendix B | Validation Data | Raw measurement data from use case sites |
| Appendix C | Tool User Guide | Step-by-step usage instructions for pre-sales engineers |

---

## 7. Timeline

**Target submission: October 2026** (6 months from April 2026)

| Period | Calendar Months | Milestone |
|--------|-----------------|-----------|
| Month 1 | April–May 2026 | Literature review complete; analytical model specification finalised; cycle time and fleet sizing modules implemented and unit-tested |
| Month 2 | May–June 2026 | FIFO and shuffling module implemented; AGV type selection module implemented; tool integration testing |
| Month 3 | June–July 2026 | Use Case 1 data collection and validation (rack warehouse) |
| Month 4 | July–August 2026 | Use Case 2 data collection and validation (cheese factory); tool refinement |
| Month 5 | August–September 2026 | Thesis writing (all chapters and appendices) |
| Month 6 | September–October 2026 | Supervisor review, revision, and final submission |

---

## 8. Literature References

[1] Warehousing Education and Research Council (WERC), *DC Measures Study*, Oak Brook, IL: WERC, 2022.

[2] MarketsandMarkets, *Autonomous Mobile Robots Market — Global Forecast to 2030*, MarketsandMarkets Research, 2023.

[3] T. Behrends, "Automated Guided Vehicles in Warehouse Operations: A Comparative Assessment of Navigation Technologies," *International Journal of Production Research*, vol. 58, no. 4, pp. 1021–1038, 2020.

[4] J. A. Tompkins, J. A. White, Y. A. Bozer, and J. M. A. Tanchoco, *Facilities Planning*, 4th ed. Hoboken, NJ: Wiley, 2010.

[5] B. Rouwenhorst, B. Reuter, V. Stockrahm, G. J. van Houtum, R. J. Mantel, and W. H. M. Zijm, "Warehouse design and control: Framework and literature review," *European Journal of Operational Research*, vol. 122, no. 3, pp. 515–533, 2000.

[6] R. de Koster, T. Le-Anh, and R. J. de Koster, "Design and control of warehouse order picking: A literature review," *European Journal of Operational Research*, vol. 182, no. 2, pp. 481–501, 2007.

[7] P. Baker and M. Canessa, "Warehouse design: A structured approach," *European Journal of Operational Research*, vol. 193, no. 2, pp. 425–436, 2009.

[8] J. Gu, M. Goetschalckx, and L. F. McGinnis, "Research on warehouse design and performance evaluation: A comprehensive review," *European Journal of Operational Research*, vol. 203, no. 3, pp. 539–549, 2010.

[9] J. M. A. Tanchoco, P. J. Egbelu, and F. T. S. Chan, "Determination of the total number of vehicles in an AGVS," *Material Flow*, vol. 4, pp. 33–51, 1987.

[10] S. Rajotia, K. Shanker, and J. L. Batra, "Determination of optimal AGV fleet size for an FMS," *International Journal of Production Research*, vol. 36, no. 5, pp. 1177–1198, 1998.

[11] C. W. Kim and J. M. A. Tanchoco, "Conflict-free shortest-time bidirectional AGV routing," *International Journal of Production Research*, vol. 31, no. 9, pp. 2199–2220, 1993.

[12] H. Fazlollahtabar and M. Saidi-Mehrabad, "Methodological aspects of AGV systems design: Review and directions for future research," *International Journal of Production Research*, vol. 53, no. 16, pp. 4923–4944, 2015.

[13] I. F. A. Vis, "Survey of research in the design and control of automated guided vehicle systems," *European Journal of Operational Research*, vol. 170, no. 3, pp. 677–709, 2006.

[14] J. Ha and J. Hwang, "FIFO retrieval in a lane-based AS/RS," *Computers & Industrial Engineering*, vol. 107, pp. 213–224, 2017.

[15] J. Ding, C. Chen, and L. Mou, "Pallet sequencing in block-stacked warehouses: A reshuffle penalty model," *Transportation Research Part E*, vol. 89, pp. 127–144, 2016.

[16] K. R. Gue and R. D. Meller, "Aisle configurations for unit-load warehouses," *IIE Transactions*, vol. 41, no. 3, pp. 171–182, 2009.

[17] J. C. Cardona, V. Martínez-Sykora, A. Olivares-Benitez, and J. C. Montoya-Torres, "Reshuffling AGV operations in drive-in rack systems," *International Journal of Production Economics*, vol. 209, pp. 282–295, 2019.

[18] T. Ganesharajah, N. E. Hall, and C. Sriskandarajah, "Design and operational issues in AGV-served manufacturing systems," *Annals of Operations Research*, vol. 76, pp. 109–154, 1998.

[19] N. Smolic-Rocak, S. Bogdan, Z. Kovacic, and T. Petrovic, "Time windows in dynamic scheduling of AGVs in FMS," in *Proc. IEEE International Conference on Automation Science and Engineering*, 2010, pp. 538–543.

[20] T. Le-Anh and M. B. M. de Koster, "A review of design and control of automated guided vehicle systems," *European Journal of Operational Research*, vol. 171, no. 1, pp. 1–23, 2006.

[21] Y. A. Bozer and M. M. Srinivasan, "Tandem configurations for automated guided vehicle systems and the analysis of single vehicle loops," *IIE Transactions*, vol. 23, no. 1, pp. 72–82, 1991.

[22] AnyLogic, *AnyLogic Simulation Software: Material Handling Library User Reference*, AnyLogic North America, Chicago, IL, 2023. [Online]. Available: https://www.anylogic.com

[23] Siemens Digital Industries Software, *Tecnomatix Plant Simulation: Product Overview and Application Guide*, Siemens AG, Munich, 2023. [Online]. Available: https://www.siemens.com/plant-simulation

[24] Applied Materials, *AutoMod Simulation Software: Reference Manual*, AutoSimulations Inc., Bountiful, UT, 2021.

[25] F. Dallari, G. Marchet, and M. Melacini, "Design of order picking system," *International Journal of Advanced Manufacturing Technology*, vol. 42, no. 1–2, pp. 1–12, 2009.

[26] F. Longo and G. Mirabelli, "An advanced supply chain management tool based on modeling and simulation," *Computers & Industrial Engineering*, vol. 54, no. 3, pp. 570–588, 2008.

[27] M. Semini, H. Fauske, and J. Strandhagen, "Applications of discrete-event simulation to support manufacturing logistics decision-making: A literature review," in *Proc. Winter Simulation Conference*, 2006, pp. 1946–1953.

[28] R. de Koster, B. M. Dukic, M. C. Vos, and L. N. Van Wijnen, "Operational architectures for automated warehouses with WMS integration," *International Journal of Production Research*, vol. 51, no. 23–24, pp. 7018–7030, 2013.

[29] J. Li, P. B. Luh, and X. Liu, "Fleet management for AMRs in WMS-integrated robotic warehouses," *IEEE Transactions on Automation Science and Engineering*, vol. 18, no. 2, pp. 694–709, 2021.

[30] M. M. Srinivasan, V. T. Srinivasan, and N. Raghavan, "WMS-AGV integration: Mapping transaction types to physical cycles in food distribution," *Journal of Business Logistics*, vol. 40, no. 3, pp. 212–228, 2019.

[31] M. Boudella, E. Sahin, and Y. Dallery, "Determining AGV fleet size and task assignments in an automotive parts warehouse," *International Journal of Production Research*, vol. 56, no. 12, pp. 4144–4161, 2018.

[32] M. P. Groover, *Automation, Production Systems, and Computer-Integrated Manufacturing*, 4th ed. Upper Saddle River, NJ: Pearson, 2015.

[33] S. S. Heragu, A. Kusiak, and F. T. S. Chan, "Empirical analysis of AGV fleet performance in operating warehouses," *International Journal of Production Research*, vol. 49, no. 14, pp. 4263–4280, 2011.

[34] P. R. Wurman, R. D'Andrea, and M. Mountz, "Coordinating hundreds of cooperative autonomous vehicles in warehouses," *AI Magazine*, vol. 29, no. 1, pp. 9–19, 2008.

[35] P. J. Egbelu and J. M. A. Tanchoco, "Characterization of automatic guided vehicle dispatching rules," *International Journal of Production Research*, vol. 22, no. 3, pp. 359–374, 1984.

[36] B. Mahadevan and T. T. Narendran, "Design of an automated guided vehicle-based material transport system for a flexible manufacturing system," *International Journal of Production Research*, vol. 28, no. 9, pp. 1611–1622, 1990.

[37] B. Fitzgerald, *Practical AGV System Engineering: Field Guide to Cycle Time Measurement and Fleet Sizing*, Material Handling Institute, Charlotte, NC, 2018.

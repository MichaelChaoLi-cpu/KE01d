# AnaSOP
Analysis Standard Operating Procedure

## 1. Research Objective

### Central Research Question

- Research question: Under the water outages reported after the 2026 Kumamoto earthquake,
  how can emergency water demand, access to distribution points, and minimum operational
  capacity be jointly estimated, and how should limited tankers and temporary distribution
  points be allocated under road and resource constraints to minimize unmet minimum water
  need?
- Why it matters: Emergency reports identify outages, distribution points, shelters, road
  restrictions, and tanker deployment separately. Decision-makers need these elements
  translated into a coherent and auditable resource-allocation plan.
- Data support currently visible: The evidence base includes 31 situation-report snapshots,
  36 announced emergency water points, 41 current public shelters, 680 road-restriction
  observations, small-area population and household data, age-disaggregated population
  groups, a routable road network, and candidate public facilities.
- Key readable variables or data scope: Current Outage Households, Evacuee People, Water
  Status, Tanker Total, Water Point Name, Latitude, Longitude, Geometry JSON, population and
  household counts, older population, road travel time, and candidate-site attributes.
- What would verify it: The study must produce internally consistent demand ranges,
  accessibility gaps, operational capacity requirements, feasible allocation scenarios, and
  remaining unmet demand, with all assumptions and uncertainty bounds reported.
- What would falsify or weaken it: The central question would be weakened if outage geography
  cannot be represented below the municipality level, most operating locations cannot be
  resolved, or tanker capacity and replenishment assumptions cannot support defensible
  scenarios.
- Required next feasibility check: Confirm spatial linkage coverage, demand-allocation
  assumptions, usable road-network coverage, candidate-site suitability, and the minimum
  operational parameters required for tanker scenarios.

### Supporting Research Questions

#### Supporting Point 1: Outage Population and Emergency Water Demand

- Role relative to central point: deepen the demand component.
- Research question: How many people are plausibly affected by reported household water
  outages, and how much emergency water is required per grid cell and municipality under
  alternative outage-population bounds and per-capita demand scenarios?
- Why it matters: Reported household outages are not directly equivalent to affected people
  or liters of daily need.
- Data support currently visible: Complete small-area population and household counts are
  available for 62,945 125 m population cells, while Current Outage Households is observed
  repeatedly for affected reporting units and Evacuee People is observed at current shelters.
- Key readable variables or data scope: Municipality, Current Outage Households, Maximum
  Outage Households, Evacuee People, Total Population, Total Households, and population-grid
  geometry.
- What would verify it: Municipal aggregation must reproduce the reported outage totals under
  the stated allocation rule, and sensitivity bounds must show how estimates change with the
  outage allocation and per-capita demand assumptions.
- What would falsify or weaken it: Results would be weakened if outages are concentrated in
  specific utility service zones that differ substantially from municipality-wide household
  distributions.
- Required next feasibility check: Verify municipality joins, define outage-population lower
  and upper bounds, confirm whether shelter evacuees require a double-counting adjustment,
  and verify official emergency-water guidance before labeling any scenario a standard.

#### Supporting Point 2: Water-Point Accessibility and Priority Populations

- Role relative to central point: evaluate spatial heterogeneity and priority populations.
- Research question: What share of affected residents, older residents, and shelter evacuees
  lies beyond specified walking or road-network thresholds from an announced emergency water
  point, and where are the largest accessibility gaps?
- Why it matters: Nominal availability of a distribution point does not imply practical
  access, especially for older residents and people at shelters without water.
- Data support currently visible: Network-access nodes are available for almost all population
  cells, age-disaggregated population is available for 36,657 disclosure groups, and current
  water-point and shelter records include location-resolution status.
- Key readable variables or data scope: Water Point Name, Latitude, Longitude, Location
  Resolution Status, Shelter Name, Evacuee People, Water Status, Population Age 65+, network
  access nodes, and road travel distance.
- What would verify it: Coverage counts should be stable across defensible thresholds, and all
  rejected network snaps and unresolved facilities must be reported explicitly.
- What would falsify or weaken it: Results would be weakened if unresolved water points account
  for a large share of service or if the vehicle-oriented road network is not a credible proxy
  for pedestrian access.
- Required next feasibility check: Resolve or bound the effect of the 26 unmatched water
  points and 29 unmatched current shelters, test pedestrian-network suitability, and retain
  age data at disclosure-group support unless an uncertainty-preserving allocation is defined.

#### Supporting Point 3: Capacity Requirements and Tanker Workload

- Role relative to central point: translate demand into operational requirements.
- Research question: Under minimum, basic, and extended emergency-water scenarios, what daily
  volume, tanker fleet, and trip count would each distribution point require to serve its
  assigned demand?
- Why it matters: A point list describes nominal service locations but does not establish that
  sufficient water or transport capacity is operating there.
- Data support currently visible: Distribution schedules and allocation limits are observed,
  tanker totals are reported by organization and time, and road travel-time attributes are
  available for routing scenarios.
- Key readable variables or data scope: Allocation Limit (L), Opening Time, Closing Time,
  Tanker Total, MLIT Tankers, JWWA Tankers, SDF Tankers, Current Outage Households, road travel
  time, and assigned demand.
- What would verify it: For every scenario, assigned demand, delivered water, vehicle capacity,
  trip time, replenishment time, unloading time, and daily work limits must balance.
- What would falsify or weaken it: Point-specific actual capacity gaps cannot be identified if
  operating capacity remains unobserved; only the capacity required to meet a target may then
  be reported.
- Required next feasibility check: Identify defensible tanker capacities, available fleet
  interpretation, operating hours, replenishment locations, storage constraints, and loading
  or unloading times.

#### Supporting Point 4: Allocation Performance, Marginal Returns, and Robustness

- Role relative to central point: broaden the analysis to allocation, robustness, and policy
  trade-offs.
- Research question: Where should limited tankers and temporary distribution points be placed
  to reduce weighted unmet demand and access burden, how much additional population is
  protected as fleet size increases, and how robust is the allocation to road disruption and
  point failure?
- Why it matters: Emergency managers need both a deployment list and the marginal benefit of
  additional resources, not a single opaque optimum.
- Data support currently visible: The evidence base includes 390,234 routable road edges,
  680 timestamped restriction observations, 6,105 candidate staging locations, emergency
  transport roads, demand nodes, and priority-facility layers.
- Key readable variables or data scope: Geometry JSON, Restriction Status, Restriction Reason,
  Restriction Start Time, Restriction Change Time, Detour Available, Isolated Settlement
  Present, candidate locations, route travel time, assigned demand, and scenario fleet size.
- What would verify it: The optimized allocation should satisfy all stated constraints and
  improve unmet-demand or access outcomes relative to transparent baselines such as nearest-
  point assignment and population-proportional allocation.
- What would falsify or weaken it: The policy value would be weakened if recommendations change
  drastically under small plausible changes in objective weights, road states, or capacity
  assumptions.
- Required next feasibility check: Confirm candidate eligibility, base and replenishment
  locations, road-restriction-to-network matching, objective weights, priority weights, and
  baseline allocation rules.

### Scope of Analysis

- Topics: Emergency water demand, spatial accessibility, minimum capacity requirements,
  tanker logistics, temporary distribution-point placement, priority populations, and
  scenario robustness.
- Geography: Kumamoto Prefecture. Demand is estimated at small-area grid or disclosure-group
  support and reported for the 45 municipalities after dissolving city wards where needed.
- Population: Residents in reporting units with water outages and people reported at public
  shelters. Hospitals and welfare facilities are priority locations, but their full clinical
  or institutional water demand is outside the first-version scope.
- Period: From the earthquake and outage onset on 2026-07-28 through the analysis cutoff on
  2026-08-08, using the latest pre-cutoff snapshot available from each source.
- Scenario scope: Per-capita demand values of 3, 10, and 20 L/person/day may be used as
  provisional sensitivity parameters until official guidance is verified. Outage duration,
  fleet size, road condition, point availability, and outage-population uncertainty are varied
  explicitly.

### Study Design Declaration

- Research type: applied
- Study design: Applied, spatially explicit, scenario-based emergency logistics planning
  study using descriptive incident evidence, network accessibility analysis, and constrained
  allocation optimization.
- Interpretation limit: The study does not estimate causal effects, predict restoration time,
  or evaluate actual water-system operations. Where operating supply capacity is not observed,
  it reports nominal access and the capacity required to satisfy a target rather than claiming
  an observed supply deficit.

## 2. Theoretical Background  /  Conceptual Framework  /  Problem Formulation

- Research type: applied
- Section focus: Empirical context, operational need, distributional access, constrained
  logistics, and cautious interpretation under incomplete supply information.

### Research Gap

Official incident information describes outage households, emergency water points, shelter
conditions, road restrictions, and tanker deployments in separate documents and at different
spatial or temporal resolutions. These records do not directly reveal the affected population,
daily water requirement, practical access to distribution, or the deployment needed to meet a
minimum target. Existing point lists also do not establish actual operating capacity. The
applied gap is therefore an integrated and uncertainty-aware planning framework that links
reported outage conditions to population demand, network access, capacity requirements,
resource allocation, and remaining unmet need without overstating what is observed.

### Conceptual Framework

The analysis follows a closed planning chain:

reported outage households

-> affected-population range

-> emergency-water demand scenarios

-> distribution-point network access

-> minimum operating-capacity requirement

-> tanker and temporary-point allocation

-> unmet demand, protected population, and marginal resource gain.

For grid or disclosure unit \(g\) in municipality \(m\), a central proportional-allocation
scenario is:

\[
N_g^{out} = N_g \min\left(1, \frac{H_m^{out}}{H_m}\right),
\]

where \(N_g\) is resident population, \(H_m^{out}\) is reported outage households, and
\(H_m\) is total households. This is an allocation model with sensitivity bounds, not a
household-level outage observation.

Demand under per-capita scenario \(s\) is:

\[
D_{g,s} = N_g^{out} q_s.
\]

Shelter demand is represented at facility locations using reported evacuee counts. Resident
and shelter demand must be reconciled or bounded so that evacuees are not silently counted
twice.

Accessibility under threshold \(d_s^{max}\) is:

\[
A_{g,s} = \mathbb{1}\left(\min_j d_{gj} \leq d_s^{max}\right),
\]

where \(d_{gj}\) is a stated walking or network distance from demand unit \(g\) to point
\(j\). Older population, shelter conditions, outage duration, and isolation indicators may
enter transparent priority weights rather than being interpreted as causal effects.

- Scope boundary: Demand, access, and logistics are scenario quantities conditional on
  reported outages and explicit assumptions. They are not measurements of individual behavior,
  queueing, actual collection, water quality, or full institutional demand.

### Problem Formulation

- Units of analysis: Population grid or disclosure group for residential demand, public shelter
  for facility demand, municipality for reporting, emergency water point or candidate location
  for service, road edge for routing, and report timestamp for incident evolution.
- Primary planning outcome: Unmet daily water demand,

\[
U_g = \max(0, D_g - S_g),
\]

where \(S_g\) is the water assigned to demand unit \(g\) through an accessible service point.
- Secondary outcomes: Population within an accepted access threshold, older and shelter
  population outside that threshold, liters and trips required by point, protected population
  share, travel burden, and marginal improvement as tankers are added.
- Allocation problem: Select temporary points and assign demand and tanker trips to minimize a
  weighted combination of unmet demand, resident access burden, and tanker travel time:

\[
\min \left[
\sum_g w_g U_g
+ \lambda \sum_{g,j} x_{gj} N_g^{out} d_{gj}
+ \gamma \sum_v T_v
\right],
\]

subject to tanker capacity, work-time, replenishment, storage, point-service, route
availability, and maximum-access constraints. The exact weights and constraints remain subject
to feasibility checking and later estimation-framework planning.
- Comparison logic: Evaluate optimized scenarios against transparent non-optimized baselines
  and report sensitivity across demand, outage duration, fleet size, road condition, point
  availability, and outage-population assumptions.
- Interpretation limit: Findings support emergency planning under stated conditions. They do
  not demonstrate causal effects or establish observed capacity shortfalls when actual supply
  capacity is unavailable.

## 3. Data Overview

### Data Scope

- Data sources reviewed: 16
- Variables summarized: 284
- Distribution plots generated: 80
- Files skipped during briefing: 0

| Data source | Rows | Columns |
| --- | ---: | ---: |
| Data source 1 | 1315 | 11 |
| Data source 2 | 1713 | 17 |
| Data source 3 | 2561 | 14 |
| Data source 4 | 1660 | 8 |
| Data source 5 | 917 | 13 |
| Data source 6 | 4470 | 15 |
| Data source 7 | 14 | 24 |
| Data source 8 | 49 | 8 |
| Data source 9 | 264 | 13 |
| Data source 10 | 198 | 66 |
| Data source 11 | 56424 | 12 |
| Data source 12 | 36657 | 19 |
| Data source 13 | 62945 | 10 |
| Data source 14 | 62945 | 16 |
| Data source 15 | 390234 | 21 |
| Data source 16 | 6105 | 17 |

### Time-Series Candidates

Potential time-series structure was detected in 8 data source(s).
Specific source files and original column names remain in the data-briefing artifacts, not in AnaSOP.

### Data Limitations

- No skipped files were recorded by the briefing script.
- Treat this section as exploratory; final variable decisions belong to Section 4.
- AnaSOP intentionally avoids raw dataset names, source file paths, and original column names.

## 4. Variable Construction  /  Key Variables

The same article-facing name is used when a concept is shared across emergency-water,
shelter, and road-status records. Shared names are listed once below. Provenance and
quality-control fields retained only for reference are documented in the preprocessing
decision record rather than treated as final analytical variables.

| variable_name | full_name | role | formal_definition | construction_or_coding | is_final_variable |
|---|---|---|---|---|---|
| Municipality | Municipality | geography | Municipal jurisdiction associated with a record. | Trimmed source label; encoded as a category. | yes |
| Water Point Name | Emergency Water Point Name | identifier | Named location where emergency water is distributed. | Trimmed official facility label. | yes |
| Valid From Date | Water Point Validity Start Date | time | First calendar date on which the announced operating schedule applies. | Parsed as a calendar date. | yes |
| Valid To Date | Water Point Validity End Date | time | Last calendar date on which the announced operating schedule applies. | Parsed as a calendar date. | yes |
| Opening Time | Water Point Opening Time | supply constraint | Daily announced opening time. | Preserved as local `HH:MM` text. | yes |
| Closing Time | Water Point Closing Time | supply constraint | Daily announced closing time. | Preserved as local `HH:MM` text. | yes |
| Allocation Basis | Water Allocation Basis | supply constraint | Unit to which the announced allocation limit applies. | Trimmed source label; encoded as a category. | yes |
| Allocation Limit (L) | Water Allocation Limit in Liters | supply constraint | \(q_j^{limit}\), the announced maximum liters distributed per allocation unit at point \(j\). | Parsed as numeric liters; missing values are not imputed. | yes |
| Water Type | Distributed Water Type | supply context | Reported type or intended use of distributed water. | Trimmed source label; encoded as a category. | yes |
| Source Status Time | Water Point Status Timestamp | time | Timestamp at which the announced water-point status applies. | Parsed and normalized to Asia/Tokyo. | yes |
| Latitude | Facility Latitude | geography | Geographic latitude in decimal degrees. | Filled only by a unique municipality-consistent normalized-name match; otherwise missing. | yes |
| Longitude | Facility Longitude | geography | Geographic longitude in decimal degrees. | Filled only by a unique municipality-consistent normalized-name match; otherwise missing. | yes |
| Location Resolution Status | Facility Location Resolution Status | quality | Indicates whether coordinates were resolved by the accepted deterministic linkage rule. | `matched_exact_2012_facility` or `unmatched`; no fuzzy matches accepted. | yes |
| Shelter Number | Shelter Sequence Number | identifier | Official sequence number within the shelter status list. | Parsed as a nullable integer. | yes |
| Shelter Name | Shelter Facility Name | identifier | Named public shelter facility. | Trimmed official facility label. | yes |
| District | Shelter District | geography | Local district associated with a shelter. | Trimmed source label; encoded as a category. | yes |
| Maximum Capacity | Maximum Shelter Capacity | supply capacity | \(C_j\), the reported maximum number of people that shelter \(j\) can accommodate. | Parsed as a nullable integer; missing values are not imputed. | yes |
| Evacuee Households | Evacuee Household Count | demand | \(H_j^{evac}\), households reported at shelter \(j\) at the snapshot time. | Parsed as a nullable integer; missing values are not imputed. | yes |
| Evacuee People | Evacuee Person Count | demand | \(N_j^{evac}\), people reported at shelter \(j\) at the snapshot time. | Parsed as a nullable integer; missing values are not imputed. | yes |
| Water Status | Shelter Water Availability Status | priority | Reported availability of water at a shelter. | Symbols recoded as `available`, `partially available`, or `unavailable`. | yes |
| Electricity Status | Shelter Electricity Availability Status | priority | Reported availability of electricity at a shelter. | Symbols recoded as `available`, `partially available`, or `unavailable`. | yes |
| Air Conditioning Status | Shelter Air Conditioning Availability Status | priority | Reported availability of air conditioning at a shelter. | Symbols recoded as `available`, `partially available`, or `unavailable`. | yes |
| Toilet Count | Fixed Toilet Count | supply capacity | Number of reported fixed toilets at a shelter. | Parsed as a nullable integer; missing values are not imputed. | yes |
| Portable Toilet Count | Portable Toilet Count | supply capacity | Number of reported portable toilets at a shelter. | Parsed as a nullable integer; missing values are not imputed. | yes |
| Snapshot Time | Observation Snapshot Timestamp | time | Timestamp identifying the state represented by a shelter or road observation. | Parsed and normalized to Asia/Tokyo. | yes |
| Report Number | MLIT Situation Report Number | identifier | Sequential number of the official situation report. | Parsed as a nullable integer. | yes |
| Report Timestamp | Situation Report Timestamp | time | Official issue timestamp of the situation report. | Parsed and normalized to Asia/Tokyo. | yes |
| Water Status Timestamp | Water-System Status Timestamp | time | Timestamp to which the reported water-system conditions refer. | Parsed and normalized to Asia/Tokyo. | yes |
| Reporting Unit Type | Reporting Unit Type | geography | Classification of the reporting entity, such as municipality or joint operator. | Trimmed source label; encoded as a category. | yes |
| Reporting Unit | Reporting Unit Name | geography | Named entity for which outage or tanker information is reported. | Trimmed source label; encoded as a category. | yes |
| Maximum Outage Households | Maximum Reported Outage Households | demand | \(H_{mt}^{max}\), the maximum reported outage households for unit \(m\) in report \(t\). | Parsed as a nullable integer; report revisions are preserved. | yes |
| Current Outage Households | Current Reported Outage Households | demand | \(H_{mt}^{out}\), households reported without water for unit \(m\) in report \(t\). | Parsed as a nullable integer; missing reports remain missing. | yes |
| Outage Period | Reported Outage Period | time | Source description of the outage start or duration. | Trimmed text; no unsupported duration is inferred. | yes |
| Damage Status | Water-System Damage Status | context | Source description of water-system damage or restoration conditions. | Trimmed text; retained without automatic classification. | yes |
| Tanker Total | Total Reported Water Tankers | supply | \(V_{mt}\), total tankers reported for unit \(m\) in report \(t\). | Parsed as a nullable integer; unreported values remain missing rather than zero. | yes |
| MLIT Tankers | Ministry of Land, Infrastructure, Transport and Tourism Tankers | supply | \(V_{mt}^{MLIT}\), tankers attributed to MLIT. | Parsed as a nullable integer; unreported values remain missing rather than zero. | yes |
| JWWA Tankers | Japan Water Works Association Tankers | supply | \(V_{mt}^{JWWA}\), tankers attributed to JWWA. | Parsed as a nullable integer; unreported values remain missing rather than zero. | yes |
| SDF Tankers | Japan Self-Defense Forces Tankers | supply | \(V_{mt}^{SDF}\), tankers attributed to the SDF. | Parsed as a nullable integer; unreported values remain missing rather than zero. | yes |
| Prefecture Name | Prefecture Name | geography | Prefecture named in a road-restriction record. | Trimmed source label; encoded as a category. | yes |
| Municipality Name | Road Restriction Municipality Name | geography | Municipality named in a road-restriction record. | Trimmed source label; encoded as a category. | yes |
| Road Type | Road Type | network attribute | Administrative or functional road classification. | Trimmed source label; encoded as a category. | yes |
| Route Name | Route Name | network attribute | Named or numbered route affected by a restriction. | Trimmed source label. | yes |
| Start Address | Restriction Start Address | geography | Address at the reported start of a restriction. | Trimmed source text. | yes |
| End Address | Restriction End Address | geography | Address at the reported end of a restriction. | Trimmed source text. | yes |
| Restriction Type | Road Restriction Type | network constraint | Administrative class of road restriction. | Trimmed source label; encoded as a category. | yes |
| Restriction Reason | Road Restriction Reason | network constraint | Reported cause of a road restriction. | Trimmed source label; encoded as a category. | yes |
| Restriction Start Time | Road Restriction Start Timestamp | time | Time at which a restriction reportedly began. | Parsed as local time and assigned Asia/Tokyo. | yes |
| Restriction Start Status | Initial Road Restriction Status | network constraint | Restriction state reported at its start. | Trimmed source label; encoded as a category. | yes |
| Affected Length (km) | Affected Road Length in Kilometers | network constraint | \(L_r^{affected}\), reported affected length of restriction record \(r\). | Parsed as numeric kilometers; missing values are not imputed. | yes |
| Geometry JSON | Road Restriction Geometry in JavaScript Object Notation | geography | GeoJSON geometry representing the restricted road segment or point. | Retained only when valid JSON with a geometry type. | yes |
| Start Point Name | Restriction Start Point Name | network attribute | Named start point used in an alternate restriction schema. | Trimmed source text; structural missingness is preserved. | yes |
| End Point Name | Restriction End Point Name | network attribute | Named end point used in an alternate restriction schema. | Trimmed source text; structural missingness is preserved. | yes |
| Restriction Status | Current Road Restriction Status | network constraint | Restriction condition reported in the alternate schema. | Trimmed source label; encoded as a category. | yes |
| Restriction Direction | Road Restriction Direction | network constraint | Travel direction affected by a restriction. | Trimmed source label; encoded as a category. | yes |
| Restricted Length (km) | Restricted Road Length in Kilometers | network constraint | \(L_r^{restricted}\), restricted length reported in the alternate schema. | Parsed as numeric kilometers; missing values are not imputed. | yes |
| Prefecture Code | Prefecture Code | geography | Numeric prefecture identifier when supplied. | Parsed as a nullable integer; structural missingness is preserved. | yes |
| Restriction Change Time | Road Restriction Change Timestamp | time | Time at which a restriction status reportedly changed. | Parsed as local time and assigned Asia/Tokyo. | yes |
| Restriction Change Status | Changed Road Restriction Status | network constraint | Status recorded after a reported restriction change. | Trimmed source label; encoded as a category. | yes |
| Detour Available | Detour Availability Indicator | network constraint | Whether a detour is reported as available. | `有` is coded `True`, `無` is coded `False`, and missing remains missing. | yes |
| Isolated Settlement Present | Isolated Settlement Presence Indicator | priority | Whether an isolated settlement is reported. | `有` is coded `True`, `無` is coded `False`, and missing remains missing. | yes |
| Personal Injury Present | Personal Injury Presence Indicator | priority | Whether personal injury is reported with the restriction. | `有` is coded `True`, `無` is coded `False`, and missing remains missing. | yes |
| Property Damage Present | Property Damage Presence Indicator | priority | Whether property damage is reported with the restriction. | `有` is coded `True`, `無` is coded `False`, and missing remains missing. | yes |
| Power Outage Present | Power Outage Presence Indicator | priority | Whether a power outage is reported with the restriction. | `有` is coded `True`, `無` is coded `False`, and missing remains missing. | yes |

### Integrated Geospatial Inputs and Support Rules

- All integrated spatial outputs use GeoParquet with `Geometry` as the primary geometry and
  EPSG:6668 as the common coordinate reference system. Source records are retained; no
  missing-value imputation, row deletion, unsupported clipping, or silent reassignment is applied.
- The administrative source layer retains 49 units, including the five Kumamoto City wards.
  A separate 45-municipality reporting layer dissolves those wards into Kumamoto City code
  `43100`; the original 49-unit layer remains unchanged.
- Resident population and household counts remain at 125 m mesh support. Age and older-
  household measures remain at disclosure-group support and must not be copied identically to
  every constituent mesh. This avoids false precision for suppressed census cells.
- Network-access records retain rejected snaps: 48 mesh records and 7 disclosure-group records.
  A rejected snap is an explicit quality condition, not a reason to drop the demand unit.
- Road speeds, baseline travel times, and `Road Available = True` describe the inherited
  baseline network. They are scenario inputs, not observations of 2026 post-earthquake road
  performance.
- Candidate staging sites are reprojected from EPSG:6670 to EPSG:6668. All 159 candidates
  lacking a matched demand node remain in the output. Prior-study stress scores and selection
  flags are excluded; retained eligibility fields remain inputs requiring study-specific
  review.
- Fire facilities are historical candidate dispatch-base locations only. They do not establish
  the presence, number, capacity, or availability of water tankers.
- Water-supply areas and treatment facilities are historical MLIT P21 records with a 2010
  reference year and 2012 dataset edition. Zero served-population or maximum-supply values are
  coded missing. Maximum daily supply is retained in cubic metres per day solely as a
  historical candidate or scenario upper-bound attribute, never as observed 2026 operating
  capacity.
- The second preprocessing round constructs bounded affected-population and water-demand
  scenarios, strict facility-to-network links, and restriction-to-road-edge candidate matches.
  It does not yet calculate resident-to-point route accessibility, assigned supply, tanker trips,
  protected population, optimized allocation, or unmet demand.

| variable_name | full_name | role | formal_definition | construction_or_coding | is_final_variable |
|---|---|---|---|---|---|
| Municipality Code | Municipality Code | geography | Official code identifying an administrative reporting unit. | Retained as a string so leading zeros remain meaningful. | yes |
| Municipality Label | Municipality Reporting Label | geography | Readable label distinguishing municipalities and retained city wards. | Retained from the administrative layer; no ward dissolve is applied. | yes |
| Geometry | Primary Spatial Geometry | geography | Polygon, point, or line geometry defining the spatial support of the record. | Preserved as GeoParquet WKB and standardized to EPSG:6668. | yes |
| Mesh Code | 125 m Population Mesh Code | identifier | Identifier of the 125 m population cell. | Retained as a string; disclosure metadata remain attached. | yes |
| Disclosure Group Code | Population Disclosure Group Code | identifier | Identifier of the census disclosure support used for aggregated or suppressed cells. | Retained as a string and used to link mesh and group records. | yes |
| Disclosure Group Size | Disclosure Group Mesh Count | quality | Number of mesh cells represented by a disclosure group. | Retained as a nullable count; no disaggregation is performed. | yes |
| Disclosure Status | Population Disclosure Status | quality | Indicates whether a mesh is directly reported or represented through an aggregation group. | Retained as a categorical disclosure-control attribute. | yes |
| Total Population | Total Resident Population | demand | (N_u), resident population reported for spatial support (u). | Retained at its native mesh or disclosure-group support; no imputation or duplication across supports. | yes |
| Total Households | Total Household Count | demand | (H_u), total households reported for spatial support (u). | Retained as a nullable count at native support. | yes |
| General Households | General Household Count | demand | Number of private or general households at spatial support (u). | Retained as a nullable count at native support. | yes |
| Suppressed Source Mesh Count | Suppressed Source Mesh Count | quality | Number of suppressed source meshes represented within a disclosure group. | Retained as a nullable count and used to flag aggregation uncertainty. | yes |
| Population Age 65+ | Population Aged 65 Years or Older | priority population | (N_u^{65+}), residents aged at least 65 in disclosure group (u). | Retained only at disclosure-group support. | yes |
| Population Age 75+ | Population Aged 75 Years or Older | priority population | (N_u^{75+}), residents aged at least 75 in disclosure group (u). | Retained only at disclosure-group support. | yes |
| Population Age 85+ | Population Aged 85 Years or Older | priority population | (N_u^{85+}), residents aged at least 85 in disclosure group (u). | Retained only at disclosure-group support. | yes |
| One-Person Households | One-Person Household Count | priority population | Number of one-person households in disclosure group (u). | Retained as a nullable count at disclosure-group support. | yes |
| Households with Member Age 65+ | Households with a Member Aged 65 or Older | priority population | Number of households containing at least one person aged 65 or older. | Retained as a nullable count at disclosure-group support. | yes |
| Older Single-Person Households | Older Single-Person Household Count | priority population | Number of one-person households headed by or consisting of an older resident. | Retained as a nullable count at disclosure-group support. | yes |
| Older Couple Households | Older Couple Household Count | priority population | Number of older-couple households in disclosure group (u). | Retained as a nullable count at disclosure-group support. | yes |
| Population Age 65+ Share | Share of Population Aged 65 or Older | priority population | (N_u^{65+}/N_u) where the denominator is valid. | Retained at disclosure-group support; undefined denominators remain missing. | yes |
| Population Age 75+ Share | Share of Population Aged 75 or Older | priority population | (N_u^{75+}/N_u) where the denominator is valid. | Retained at disclosure-group support; undefined denominators remain missing. | yes |
| Population Age 85+ Share | Share of Population Aged 85 or Older | priority population | (N_u^{85+}/N_u) where the denominator is valid. | Retained at disclosure-group support; undefined denominators remain missing. | yes |
| Older Single-Person Household Share | Share of Older Single-Person Households | priority population | Older single-person households divided by the applicable household denominator. | Retained at disclosure-group support; undefined denominators remain missing. | yes |
| Older Couple Household Share | Share of Older Couple Households | priority population | Older-couple households divided by the applicable household denominator. | Retained at disclosure-group support; undefined denominators remain missing. | yes |
| Analysis Unit ID | Network Analysis Unit Identifier | identifier | Identifier linking a population support to its network-access representation. | Retained as a string; unmatched units remain present. | yes |
| Demand Node ID | Demand-Side Road Network Node Identifier | network linkage | Road-network node assigned to a population analysis unit. | Retained when the accepted snap exists; otherwise missing. | yes |
| Network Snap Distance (m) | Network Snap Distance in Metres | quality | Euclidean distance from the source support representative point to its assigned road node. | Retained as a nullable float in metres. | yes |
| Network Snap Accepted | Network Snap Acceptance Indicator | quality | Whether the source-to-network snap satisfies the preprocessing acceptance rule. | Retained as a nullable Boolean; rejected records are not removed. | yes |
| Access Road Edge ID | Access Road Edge Identifier | network linkage | Road edge used to connect an analysis unit to the routable network. | Retained as an identifier when a usable snap exists. | yes |
| Access Edge Fraction | Fractional Position on Access Edge | network linkage | Relative position of the access point along its road edge. | Retained as a nullable proportion without clipping. | yes |
| Representative Mesh Code | Representative Mesh Code for Disclosure Group | network linkage | Mesh selected to represent a disclosure group for network access. | Retained as a string; it does not redistribute group demographic totals. | yes |
| Road Edge ID | Routable Road Edge Identifier | identifier | Unique identifier of a directed or routable road edge. | Retained as a string. | yes |
| Road Section ID | Source Road Section Identifier | identifier | Identifier of the source road section from which an edge is derived. | Retained as a string. | yes |
| From Node ID | Road Edge Origin Node Identifier | network topology | Origin node of a routable edge. | Retained as a string for graph construction. | yes |
| To Node ID | Road Edge Destination Node Identifier | network topology | Destination node of a routable edge. | Retained as a string for graph construction. | yes |
| Network Component ID | Road Network Component Identifier | network topology | Connected-component identifier of a routable edge. | Retained to diagnose disconnected routing components. | yes |
| Road Length (m) | Road Edge Length in Metres | network cost | (l_e), length of road edge (e). | Retained as a nullable float in metres. | yes |
| Assumed Speed (km/h) | Assumed Baseline Road Speed | scenario parameter | (v_e^0), assumed speed for edge (e) under the inherited baseline. | Retained in kilometres per hour; not interpreted as observed post-event speed. | yes |
| Baseline Edge Travel Time (min) | Baseline Road Edge Travel Time | scenario parameter | (t_e^0=60l_e/(1000v_e^0)) where inputs are valid. | Retained in minutes as a baseline routing cost. | yes |
| Hazard Exposure Class | Road Hazard Exposure Class | network attribute | Categorical hazard-exposure classification assigned to a road edge. | Retained as a scenario attribute, not an observed closure state. | yes |
| Emergency Route Membership | Emergency Transport Route Membership | network attribute | Whether an edge belongs to a designated emergency transport route. | Retained as a network-priority attribute. | yes |
| Road Available | Baseline Road Availability Indicator | scenario parameter | Whether an edge is enabled in the inherited baseline graph. | Retained as a Boolean baseline; earthquake disruption scenarios may override it. | yes |
| Network Analysis Eligible | Network Analysis Eligibility Indicator | quality | Whether an edge satisfies inherited routing eligibility rules. | Retained as a Boolean without treating it as observed road operability. | yes |
| Route ID | Road Route Identifier | network attribute | Identifier of the named or numbered route containing an edge. | Retained as a string. | yes |
| Road Category | Road Functional or Administrative Category | network attribute | Source classification of road function or administration. | Retained as a categorical attribute. | yes |
| Road State | Road Structural State | network attribute | Source code describing the structural state or configuration of a road segment. | Retained as a categorical attribute; not interpreted as 2026 damage. | yes |
| Vertical Level | Road Vertical-Level Category | network topology | Source code distinguishing surface, elevated, tunnel, or related vertical configurations. | Retained as a categorical topology attribute. | yes |
| Width Category | Road Width Category | network attribute | Source categorical width class for a road edge. | Retained as a categorical routing attribute. | yes |
| Toll Category | Road Toll Category | network attribute | Source indicator or class describing toll status. | Retained as a categorical attribute. | yes |
| Secondary Mesh Code | Secondary Mesh Spatial Code | geography | Secondary mesh code locating a road edge. | Retained as a string. | yes |
| Candidate Staging Site ID | Candidate Staging Site Identifier | identifier | Unique identifier of a possible temporary distribution or logistics site. | Retained as a string; prior-study selection scores are excluded. | yes |
| Candidate Staging Site Type | Candidate Staging Site Type | candidate attribute | Facility class of a candidate staging location. | Retained as a categorical attribute for later eligibility rules. | yes |
| Candidate Staging Site Name | Candidate Staging Site Name | candidate attribute | Readable facility or place name of a candidate location. | Trimmed readable name retained from the candidate inventory. | yes |
| Candidate Source Status | Candidate Source Status | quality | Provenance or availability status assigned by the candidate-source inventory. | Retained as a categorical quality attribute. | yes |
| Staging Source Priority | Staging Source Priority | candidate attribute | Inherited source-priority class used to order candidate evidence. | Retained as an input; it is not the emergency-water optimization priority weight. | yes |
| Access Mesh Code | Candidate Access Mesh Code | network linkage | Population mesh associated with a candidate's network-access representation. | Retained as a string when available. | yes |
| Staging Demand Node ID | Candidate Staging Road Network Node Identifier | network linkage | Road node assigned to a candidate staging location. | Retained when available; 159 unmatched candidates remain with missing nodes. | yes |
| Staging Access Network Snap Distance (m) | Candidate-to-Network Snap Distance | quality | Distance from a candidate staging site to its assigned road-network node. | Retained as a nullable float in metres. | yes |
| Staging-to-Mesh Distance (m) | Candidate-to-Access-Mesh Distance | quality | Distance from a staging candidate to its associated access mesh. | Retained as a nullable float in metres. | yes |
| Candidate Network Eligible | Candidate Network Eligibility Indicator | quality | Whether the candidate satisfies the inherited network-eligibility rule. | Retained as a Boolean input requiring study-specific review. | yes |
| Screened Staging Candidate | Screened Staging Candidate Indicator | candidate attribute | Whether the location passed the inherited general staging screen. | Retained as a Boolean input, not as a final emergency-water site decision. | yes |
| Fire Facility Name | Fire Facility Name | candidate attribute | Readable name of a historical fire-service facility. | Retained as a possible dispatch-base label. | yes |
| Fire Facility Type Code | Fire Facility Type Code | candidate attribute | Source code classifying a fire-service facility. | Retained as a categorical code. | yes |
| Address | Facility Address | geography | Reported street address of a candidate facility. | Trimmed source text; no missing address is imputed. | yes |
| Fire Facility Type | Fire Facility Type | candidate attribute | Readable class of a fire-service facility. | Retained as a categorical attribute. | yes |
| Candidate Dispatch Base | Candidate Dispatch Base Indicator | candidate attribute | Whether a historical fire facility is eligible for consideration as a dispatch base. | Retained as a Boolean candidate flag; it does not imply an available tanker fleet. | yes |
| Water Utility Operator | Historical Water Utility Operator | supply context | Operator named in the historical waterworks record. | CP932 text decoded and whitespace trimmed. | yes |
| Water Service Name | Historical Water Service Name | supply context | Named water service associated with a historical supply area or treatment facility. | CP932 text decoded and whitespace trimmed. | yes |
| Water Service Type Code | Historical Water Service Type Code | supply context | Numeric class of the historical water service. | Parsed as a nullable integer. | yes |
| Served Population | Historical Served Population | historical capacity context | Population reported as served by a P21 water-supply-area record in 2010. | Parsed as a nullable integer; zero is treated as missing. | yes |
| Maximum Daily Supply (m3/day) | Historical Maximum Daily Water Supply | historical capacity context | Reported historical maximum daily supply in cubic metres per day. | Parsed as a nullable float; zero is treated as missing and values are not treated as 2026 operating capacity. | yes |
| Source Reference Year | Source Reference Year | provenance | Calendar year represented by the historical P21 attributes. | Set to 2010 for every P21 record. | yes |
| Dataset Edition Year | Dataset Edition Year | provenance | Publication or dataset edition year of the P21 layer. | Set to 2012 for every P21 record. | yes |
| Historical Capacity Only | Historical Capacity Interpretation Indicator | interpretation constraint | Indicates that population and supply attributes are historical scenario inputs only. | Set to `True` for every P21 record. | yes |
| Water Treatment Facility Name | Historical Water Treatment Facility Name | candidate attribute | Name of a P21 treatment or purification facility. | CP932 text decoded and whitespace trimmed; facility presence and operation in 2026 remain unverified. | yes |

### Second-Round Linkage and Scenario Construction

- The reporting-unit crosswalk contains 15 exact Kumamoto municipality matches, three
  explicitly out-of-scope units in neighboring prefectures, and one joint operator retained
  without unsupported municipal allocation.
- Each population mesh is linked to a reporting municipality by a point-in-polygon match when
  unique, then by maximum polygon overlap when necessary. The resulting statuses are 62,507
  unique point matches, 432 maximum-overlap matches, and six unmatched meshes. Unmatched
  meshes, including their 41 residents and 17 households, remain in the analytical output.
- Let \(N_g\) and \(H_g\) be population and households in mesh \(g\), and let
  \(H_m^{out}\) and \(H_m\) be reported outage households and total households in
  municipality \(m\). The household-equivalent outage allocation is
  \[
  h_g^{out}=H_m^{out}\frac{H_g}{H_m}.
  \]
  The lower, central, and upper affected-population scenarios are
  \[
  N_g^{lower}=\min(N_g,h_g^{out}),
  \]
  \[
  N_g^{central}=N_g\min\left(1,\frac{H_m^{out}}{H_m}\right),
  \]
  and
  \[
  N_g^{upper}=\min(N_g,h_g^{out}s_m^{90}),
  \]
  where \(s_m^{90}\) is the household-count-weighted 90th percentile of persons per
  household among meshes in municipality \(m\). These are planning sensitivity bounds, not
  confidence intervals or household-level confirmations.
- Reported zero outage households generate zero affected population. An absent outage report
  remains missing. Ratios above one are capped at one and explicitly flagged. Maximum reported
  outage households remain a historical peak measure rather than an upper bound for the current
  snapshot.
- For \(q\in\{3,10,20\}\) liters per person per day, resident demand is
  \[
  D_{g,q}=N_g^{scenario}q.
  \]
  Shelter demand is constructed separately as \(D_{j,q}^{shelter}=N_j^{evac}q\) and is not
  automatically added to resident demand, preventing unverified double counting.
- Facility coordinates follow a strict hierarchy: an already accepted event coordinate, an
  exact historical-facility match, or a normalized exact candidate match only when all matching
  records share one geometry. No fuzzy matching is used. Seventeen of 36 water points and 17 of
  41 shelters are resolved; all 34 resolved facilities have an accepted road-node snap within
  250 m. Unresolved facilities remain in the outputs with missing network fields.
- All 680 road-restriction observations are retained. Line restrictions match every edge within
  50 m; point restrictions match the nearest edge within 100 m; a nearest-edge fallback within
  250 m is allowed when the primary rule finds no edge. Route-name agreement is auxiliary only.
  The match result contains 604 observations with at least one candidate edge and 76 unmatched
  observations. A matched edge is a restriction candidate and is not automatically coded closed.
- Scenario assumptions are stored in long format. The parameter value remains text so numeric
  and categorical levels share one schema. Evidence class distinguishes official reference
  values from researcher-defined sensitivity assumptions.

| variable_name | full_name | role | formal_definition | construction_or_coding | is_final_variable |
|---|---|---|---|---|---|
| Network Node ID | Road Network Node Identifier | identifier | Unique identifier of a routable road-network node. | Retained as a string for graph and facility linkage. | yes |
| Dispatch Base Node ID | Dispatch-Base Road Network Node Identifier | network linkage | Road node linked to a candidate dispatch base. | Retained for an accepted snap; otherwise missing. | yes |
| Reporting Prefecture | Reporting Prefecture | geography | Prefecture associated with a reporting unit. | Standardized readable English name; encoded as a category. | yes |
| Reporting Municipality Code | Reporting Municipality Code | geography | Code of the 45-unit Kumamoto reporting geography. | Retained as a string; Kumamoto City wards are represented by `43100`. | yes |
| Reporting Municipality Name | Reporting Municipality Name | geography | English name of the matched reporting municipality. | Assigned only through the explicit reporting-unit crosswalk or spatial linkage. | yes |
| Municipality Match Status | Reporting-Unit Municipality Match Status | quality | Outcome of reporting-unit linkage to the study geography. | Coded as exact in-scope, outside scope, joint operator unallocated, or unmatched. | yes |
| In Kumamoto Study Area | Kumamoto Study-Area Indicator | geography | Whether a reporting unit belongs to the Kumamoto study area. | Boolean derived from the explicit crosswalk. | yes |
| Joint Operator Area Status | Joint-Operator Area Status | quality | Whether a reporting unit represents a multi-municipality operator. | Boolean; joint operators are retained without unsupported allocation. | yes |
| Constituent Administrative Unit Count | Constituent Administrative Unit Count | geography | Number of source administrative units dissolved into a reporting municipality. | Equals five for Kumamoto City and one for other reporting municipalities. | yes |
| Kumamoto City Ward Dissolved | Kumamoto City Ward-Dissolve Indicator | geography | Whether the reporting polygon combines Kumamoto City wards. | Boolean assigned during creation of the 45-municipality layer. | yes |
| Outage Observation Status | Outage Observation Status | quality | Availability and interpretation of the outage observation for a municipality. | Distinguishes reported positive, reported zero, absent report, and unmatched geography. | yes |
| Municipality Total Population | Municipality Total Resident Population | demand denominator | \(N_m=\sum_{g\in m}N_g\), resident population assigned to municipality \(m\). | Summed from linked 125 m meshes; unmatched meshes remain separate audit rows. | yes |
| Municipality Total Households | Municipality Total Household Count | demand denominator | \(H_m=\sum_{g\in m}H_g\), households assigned to municipality \(m\). | Summed from linked 125 m meshes; missing values are not imputed. | yes |
| Outage Household Ratio | Reported Outage Household Ratio | demand | \(r_m=\min(1,H_m^{out}/H_m)\) when inputs are valid. | Values above one are capped and flagged; absent reports remain missing. | yes |
| Outage Population Scenario | Affected-Population Scenario | scenario | Scenario label identifying lower, central, or upper affected population. | Encoded as an ordered categorical sensitivity level. | yes |
| Estimated Outage Population | Estimated Population Affected by Outage | demand | \(N_g^{scenario}\), affected residents under the selected planning bound. | Constructed using the documented lower, central, and upper formulas. | yes |
| Demand Scenario | Per-Capita Water-Demand Scenario | scenario | Scenario label for minimum, basic, or extended daily water demand. | Maps to 3, 10, or 20 L/person/day. | yes |
| Per Capita Water Demand (L/person/day) | Per-Capita Emergency Water Demand | scenario parameter | \(q\), liters required per person per day under a demand scenario. | Set to 3, 10, or 20 for sensitivity analysis. | yes |
| Estimated Water Demand (L/day) | Estimated Resident Emergency Water Demand | outcome | \(D_{g,q}=N_g^{scenario}q\), liters per day required by a mesh. | Computed for every estimable population and demand scenario pair. | yes |
| Spatial Join Status | Population-Mesh Spatial Join Status | quality | Method and success state of mesh-to-municipality linkage. | Unique point match, maximum-overlap match, or unmatched. | yes |
| Municipality Household Share | Mesh Share of Municipality Households | allocation weight | \(H_g/H_m\) when the denominator is valid. | Used to allocate reported outage households to meshes. | yes |
| Outage Snapshot Time | Outage Observation Snapshot Timestamp | time | Timestamp represented by the selected outage report. | Parsed and normalized to Asia/Tokyo; absent observations remain missing. | yes |
| Location Resolution Source | Facility Location Resolution Source | provenance | Evidence source used to assign a facility geometry. | Accepted event coordinate, exact historical match, unique normalized exact match, or unresolved. | yes |
| Location Match Candidate Record Count | Facility Location Candidate Record Count | quality | Number of candidate records returned by deterministic name matching. | Retained as a nullable integer for ambiguity auditing. | yes |
| Location Match Candidate Geometry Count | Facility Location Candidate Geometry Count | quality | Number of unique geometries among deterministic location candidates. | A new match is accepted only when this count equals one. | yes |
| Water Point Node ID | Emergency Water-Point Road Network Node Identifier | network linkage | Road node assigned to an emergency water point. | Retained only for an accepted snap within 250 m. | yes |
| Shelter Node ID | Shelter Road Network Node Identifier | network linkage | Road node assigned to a public shelter. | Retained only for an accepted snap within 250 m. | yes |
| Estimated Shelter Water Demand (L/day) | Estimated Shelter Emergency Water Demand | demand | \(D_{j,q}^{shelter}=N_j^{evac}q\), shelter demand in liters per day. | Computed separately for 3, 10, and 20 L/person/day when evacuee count is observed. | yes |
| Shelter Demand Accounting Status | Shelter Demand Accounting Status | interpretation constraint | Indicates how shelter demand relates to resident demand. | Set to separate accounting; no automatic resident-demand addition is performed. | yes |
| Restriction Observation ID | Road Restriction Observation Identifier | identifier | Unique identifier of a retained road-restriction observation. | Assigned before edge matching so all 680 observations remain auditable. | yes |
| Matched Road Edge ID | Restriction-Matched Road Edge Identifier | network linkage | Candidate road edge spatially associated with a restriction observation. | One row per candidate edge; missing for unmatched observations. | yes |
| Road Edge Match Distance (m) | Restriction-to-Road-Edge Match Distance | quality | Minimum spatial distance between a restriction geometry and candidate edge. | Calculated in metres under the primary or fallback threshold. | yes |
| Route Name Agreement | Restriction and Road Route-Name Agreement | quality | Whether normalized route names agree when both are available. | Auxiliary Boolean; it does not override spatial matching. | yes |
| Road Edge Match Candidate Count | Road Edge Match Candidate Count | quality | Number of road-edge candidates associated with a restriction observation. | Counted after applying geometry-specific thresholds. | yes |
| Road Edge Match Method | Road Edge Match Method | quality | Spatial rule used to identify the candidate road edge. | Line buffer, point nearest, fallback nearest, or unmatched. | yes |
| Road Edge Match Status | Road Edge Match Status | quality | Whether at least one candidate edge was identified. | Matched or unmatched; it does not imply a road closure. | yes |
| Parameter Name | Scenario Parameter Name | scenario parameter | Readable name of a planning assumption. | Stored in a long-format scenario table. | yes |
| Scenario Level | Scenario Parameter Level | scenario parameter | Label identifying a parameter's sensitivity level or categorical state. | Retained as text for ordering and display. | yes |
| Parameter Value | Scenario Parameter Value | scenario parameter | Numeric or categorical value assigned to a scenario level. | Stored as text to support a common schema. | yes |
| Parameter Unit | Scenario Parameter Unit | scenario parameter | Measurement unit associated with a scenario parameter. | Retained as readable text; categorical parameters use a nonnumeric unit label. | yes |
| Evidence Class | Scenario Parameter Evidence Class | provenance | Classification of the evidentiary basis for an assumption. | Distinguishes official reference from researcher-defined sensitivity values. | yes |
| Evidence Source | Scenario Parameter Evidence Source | provenance | Citation or description supporting a parameter value. | Retained as readable text; researcher-defined values are labeled accordingly. | yes |
| Parameter Notes | Scenario Parameter Notes | interpretation constraint | Qualification governing the interpretation or use of a parameter. | Retained as text and never used as an unrecorded operational assumption. | yes |

## 5. Identification Strategy

### Design Principle

This is a descriptive, spatially explicit, scenario-based planning study rather than a
causal design. Identification means that each reported outage condition is mapped through
predeclared population, access, transport, and allocation rules to a reproducible set of
planning outcomes. Differences across scenarios identify the consequences of assumptions
within the model; they do not identify causal effects, realized emergency operations, or
restoration dynamics.

### Evidence Layers and Analytical Targets

The framework separates three evidence layers:

- Observed incident evidence includes Current Outage Households, Outage Snapshot Time,
  Evacuee People, Water Status, announced Water Point Name and schedules, reported Tanker
  Total, and road-restriction attributes.
- Constructed analytical evidence includes Estimated Outage Population, Estimated Water
  Demand (L/day), Estimated Shelter Water Demand (L/day), Reporting Municipality Code,
  Water Point Node ID, Shelter Node ID, Dispatch Base Node ID, and Matched Road Edge ID.
- Assumed planning inputs are identified by Parameter Name, Scenario Level, Parameter Value,
  Parameter Unit, and Evidence Class. Historical Capacity Only and Source Reference Year
  prevent historical waterworks attributes from being interpreted as current capacity.

The analytical targets are: bounded affected population and daily demand; nominal network
coverage; required water, trip, and vehicle capacity; minimum unmet demand under a limited
fleet; protected-population gains from added vehicles; and deployment stability across road
and water-point failures.

### Primary Scenario and Comparisons

The primary planning scenario uses the central Outage Population Scenario, minimum Demand
Scenario of 3 L/person/day, 3-day Outage Duration, 3,000 L Tanker Capacity, five Daily Trip
Limit, 30-minute Loading Time and Unloading Time, 10-hour Daily Work Limit, 500 m General
Access Distance, 250 m Older Resident Access Distance, fleet size of 10, baseline Road State,
and reported-schedule Water Point State. These are reference settings, not observed 2026
operational facts.

Resident demand and shelter demand remain separate analytical ledgers. Shelter demand is
never automatically added to resident demand. The resident ledger answers population-wide
planning questions, while the shelter ledger reports the additional requirement implied by
Evacuee People and prioritizes shelters with unavailable or partially available Water Status.
No combined total is presented without an explicit deduplication rule.

Comparisons vary lower, central, and upper outage population; 3, 10, and 20 L/person/day;
1, 3, and 7 days; fleets of 5, 10, and 20 vehicles; three road states; and reported-schedule
versus worst single-point-failure states. Vehicle capacity, trip, service-time, and work-hour
assumptions are varied one factor at a time around the primary setting unless a planned output
explicitly reports their interaction.

### Eligibility, Baselines, and Interpretation

- The resident demand unit is the 125 m Mesh Code linked through Demand Node ID. Older-resident
  accessibility is evaluated at Disclosure Group Code support using Population Age 65+ and is
  not copied to constituent meshes. Shelter accessibility uses Shelter Node ID.
- Announced points enter route-based analysis only when Water Point Node ID is present and
  Network Snap Accepted is true. Unresolved points remain in audit denominators and explicit
  optimistic bounds, but are not assigned fabricated coordinates.
- Temporary sites require Screened Staging Candidate, Candidate Network Eligible, and Staging
  Demand Node ID. Dispatch bases require Candidate Dispatch Base and Dispatch Base Node ID.
- Water Treatment Facility Name and Geometry define historical refill candidates. Maximum
  Daily Supply (m3/day) is used only in a labeled historical upper-bound sensitivity and never
  as verified 2026 supply.
- The transparent access baseline assigns each reachable demand unit to its nearest eligible
  announced point. The transparent allocation baseline assigns limited delivered volume in
  proportion to demand within each point's feasible service area. Optimization must improve
  or explain failure to improve these baselines.

The planned figures and tables can support all five research questions only within these
scenario boundaries. They cannot establish observed point-level capacity gaps, actual tanker
availability, realized trips, causal effects, restoration time, or a validated real-time
deployment order.

## 6. Main Estimation Framework

### Demand Estimation

Daily resident demand is

\[
D_{g,s,q}=N_{g,s}^{out}q.
\]

Here, \(g\) is a 125 m population mesh, \(s\) is the lower, central, or upper
Outage Population Scenario, \(q\) is Per Capita Water Demand (L/person/day),
\(N_{g,s}^{out}\) is Estimated Outage Population, and \(D_{g,s,q}\) is Estimated
Water Demand (L/day).

Daily shelter demand is estimated separately as

\[
D_{h,q}^{shelter}=N_h^{evac}q.
\]

Here, \(h\) is a shelter, \(N_h^{evac}\) is Evacuee People, and
\(D_{h,q}^{shelter}\) is Estimated Shelter Water Demand (L/day). The previously
defined \(q\) is reused. Shelter Demand Accounting Status must remain separate.

Municipal resident demand is

\[
D_{m,s,q}^{resident}=\sum_{g\in\mathcal{G}_m}D_{g,s,q}.
\]

Here, \(m\) is Reporting Municipality Code, \(\mathcal{G}_m\) is the set of meshes
linked to municipality \(m\), and \(D_{m,s,q}^{resident}\) is daily municipal resident
demand. Unmatched meshes are reported as a separate audit unit.

Cumulative resident demand over an outage-duration scenario is

\[
V_{m,s,q,\delta}^{resident}=\delta D_{m,s,q}^{resident}.
\]

Here, \(\delta\) is Outage Duration in days and \(V_{m,s,q,\delta}^{resident}\) is
cumulative municipal resident water volume. It is a planning total, not a restoration forecast.

### Nominal Network Accessibility

For each Road State \(r\), the eligible road graph retains Road Edge ID records allowed
by Road Available and Network Analysis Eligible. Baseline Edge Travel Time (min) is used for
tanker routing, while Road Length (m) is used as the nominal pedestrian-access proxy.
Network distance is

\[
d_{uj}^{r}=\min_{\pi\in\mathcal{P}_{uj}^{r}}\sum_{e\in\pi}l_e.
\]

Here, \(u\) is a resident mesh, older-population disclosure group, or resolved shelter;
\(j\) is an eligible water point; \(\mathcal{P}_{uj}^{r}\) is the set of network paths
from \(u\) to \(j\) under road state \(r\); \(e\) is a Road Edge ID on path
\(\pi\); \(l_e\) is Road Length (m); and \(d_{uj}^{r}\) is shortest network distance.
If no path exists or either node is missing, distance is undefined and the unit is not counted
as covered.

For population class \(x\), access-distance threshold \(a\), road state \(r\), and
Water Point State \(o\), weighted coverage is

\[
C_{x,a,r,o}=\frac{\sum_{u\in\mathcal{U}_x}w_u^x
\mathbf{1}\left(\min_{j\in\mathcal{J}_o}d_{uj}^{r}\leq a\right)}
{\sum_{u\in\mathcal{U}_x}w_u^x}.
\]

Here, \(x\) identifies affected residents, residents aged 65 or older, or shelter
evacuees; \(\mathcal{U}_x\) is the corresponding set of analysis units;
\(w_u^x\) is Estimated Outage Population, Population Age 65+, or Evacuee People;
\(a\) is General Access Distance or Older Resident Access Distance;
\(\mathcal{J}_o\) is the set of eligible points under state \(o\);
\(\mathbf{1}(\cdot)\) is the indicator function; and \(C_{x,a,r,o}\) is the
covered share. Every denominator, unresolved count, rejected snap, and disconnected unit is
reported.

The resolved-point estimate is the conservative location-evidence result. An explicitly
optimistic upper bound additionally treats uncovered demand in a municipality containing an
unresolved announced point as potentially coverable, without assigning a distance. This bound
cannot be interpreted as actual access. Resolved shelters are analyzed conditionally, while
unresolved shelters and their Evacuee People are reported as an unknown-access share.

Road State is implemented as follows:

- `baseline` retains the inherited eligible network.
- `matched_restrictions_closed` disables every Matched Road Edge ID as a stress test. The
  disabled edges remain restriction candidates rather than confirmed observed closures.
- `severe_disruption` additionally disables edges with a nonmissing Hazard Exposure Class.
  This is a researcher-defined worst-case scenario, not an observed road state.

Water Point State is implemented as follows:

- `all_resolved_points` includes every resolved announced point and is a nominal upper-coverage
  scenario.
- `reported_schedule` retains resolved points whose Valid From Date, Valid To Date, Opening
  Time, and Closing Time permit service in the analysis period.
- `single_point_failure` removes each reported-schedule point in turn and retains the worst
  result for each performance measure.

### Tanker Workload and Required Capacity

For dispatch base \(b\), historical refill candidate \(f\), and water point \(j\),
the feasible trips per tanker per day are

\[
K_{bfj}=\min\left\{K^{limit},\max\left[0,
\left\lfloor\frac{60W-2t_{bf}}{2t_{fj}+t^{load}+t^{unload}}\right\rfloor\right]\right\}.
\]

Here, \(K_{bfj}\) is feasible daily trips per tanker; \(K^{limit}\) is Daily Trip
Limit; \(W\) is the effective Daily Work Limit in hours, reduced by reported point opening
hours when the reported-schedule state applies; \(t_{bf}\) is baseline or scenario travel
time from base \(b\) to refill candidate \(f\); \(t_{fj}\) is one-way travel time
from \(f\) to \(j\); \(t^{load}\) is Loading Time; and \(t^{unload}\) is
Unloading Time. The expression treats base-to-refill travel as one daily round trip and each
delivery as a refill-point round trip.

Deliverable volume per tanker is

\[
L_{bfj}^{deliver}=cK_{bfj}.
\]

Here, \(c\) is Tanker Capacity and \(L_{bfj}^{deliver}\) is liters deliverable per
tanker per day on route \((b,f,j)\).

For assigned point demand \(Q_j\), the required tanker count on selected route
\((b^*,f^*,j)\) is

\[
n_j^{required}=\left\lceil\frac{Q_j}{L_{b^*f^*j}^{deliver}}\right\rceil.
\]

Here, \(Q_j\) is demand assigned to point \(j\), \(b^*\) and \(f^*\) are the
selected dispatch base and refill candidate, and \(n_j^{required}\) is the required number
of tankers. A route with zero feasible trips is infeasible. Allocation Limit (L) is reported
but is not interpreted as daily point throughput. Maximum Daily Supply (m3/day) is applied
only in a separately labeled historical upper-bound sensitivity.

### Constrained Allocation

The resident and shelter ledgers are solved separately with the same network and vehicle
logic. For a demand unit \(u\), let \(D_u\) be ledger-specific demand,
\(x_{uj}\) delivered water from point \(j\), \(U_u\) unmet demand,
\(y_{uj}\) a binary assignment indicator, \(z_j\) a binary point-selection indicator,
\(v_{bfj}\) the integer tankers assigned to route \((b,f,j)\), and \(F\) Fleet Size.
Only arcs meeting the relevant access threshold and road or point state are created. The core
constraints are

\[
\sum_j x_{uj}+U_u=D_u,
\]

\[
\sum_j y_{uj}\leq 1,
\]

\[
0\leq x_{uj}\leq D_uy_{uj},
\]

\[
y_{uj}\leq z_j,
\]

\[
\sum_u x_{uj}\leq\sum_b\sum_f cK_{bfj}v_{bfj},
\]

and

\[
\sum_b\sum_f\sum_j v_{bfj}\leq F.
\]

The resident model uses the lexicographic objective

\[
\operatorname{lexmin}\left(
U^{resident},B^{older},B^{resident},T^{tanker},Z^{temporary}
\right).
\]

Here, \(U^{resident}\) is total unmet resident minimum demand; \(B^{older}\) is
network-distance burden for Population Age 65+ at disclosure-group support;
\(B^{resident}\) is affected-resident network-distance burden; \(T^{tanker}\) is total
tanker travel and service time; and \(Z^{temporary}\) is the number of selected temporary
points. Including \(B^{older}\) gives older residents access priority without adding their
population again as water demand.

The shelter model uses

\[
\operatorname{lexmin}\left(
U^{water-unavailable},U^{shelter},T^{tanker},Z^{temporary}
\right).
\]

Here, \(U^{water-unavailable}\) is unmet demand at shelters with unavailable or partially
available Water Status, and \(U^{shelter}\) is total unmet shelter demand. The previously
defined logistics terms are reused. Results from the two ledgers are displayed side by side
and are not summed.

### Performance, Marginal Returns, and Robustness

For Fleet Size \(n\) and complete scenario \(\omega\), the protected resident share is

\[
P_n(\omega)=\frac{\sum_g N_{g,s}^{out}
\mathbf{1}\left(\sum_jx_{gj}=D_{g,s,q}\right)}
{\sum_gN_{g,s}^{out}}.
\]

Here, \(n\) is the fleet size used by the model, \(\omega\) is the combination of
outage-population, demand, road, point, and operational assumptions, and \(P_n(\omega)\)
is the share of affected residents receiving the full scenario target. The remaining symbols
retain their earlier definitions.

Total unmet resident water is

\[
U_n(\omega)=\sum_gU_g.
\]

Here, \(U_n(\omega)\) is liters per day unmet under the specified fleet and scenario.

The marginal protected-population gain from the previous fleet level \(n^-\) is

\[
\Delta P_n(\omega)=P_n(\omega)-P_{n^-}(\omega).
\]

Here, \(n^-\) is the immediately smaller planned Fleet Size and
\(\Delta P_n(\omega)\) is its incremental protection gain.

Deployment stability relative to the primary scenario \(\omega_0\) is

\[
R_J(\omega)=\frac{|\mathcal{J}_{\omega}^{*}\cap\mathcal{J}_{\omega_0}^{*}|}
{|\mathcal{J}_{\omega}^{*}\cup\mathcal{J}_{\omega_0}^{*}|}.
\]

Here, \(\mathcal{J}_{\omega}^{*}\) is the set of selected temporary points under
scenario \(\omega\), \(\omega_0\) is the primary scenario, and \(R_J(\omega)\)
is Jaccard deployment stability. Low stability or sharply changing protected-population gains
weakens a single-site deployment interpretation.

### Sensitivity and Failure-Mode Plan

The Scenario Performance and Robustness table uses 162 primary factorial combinations:
three outage-population bounds, three demand levels, three fleet sizes, three road states, and
two operational point states consisting of reported schedule and worst single-point failure.
The all-resolved state is reserved for nominal access upper coverage. Tanker Capacity, Daily
Trip Limit, Loading Time, Unloading Time, Daily Work Limit, and access distances are varied
one at a time around the primary scenario. Results are stratified by municipality and by
resident, older-resident, and shelter populations where their spatial support permits.

Required failure-mode checks include disconnected demand nodes, unresolved facilities, zero
feasible trips, insufficient fleet, empty candidate sets, extreme historical refill distances,
and infeasible models. Such cases remain explicit outcomes rather than being deleted or silently
reassigned.

## 7. Analytical Workflow

The workflow proceeds from audit to demand, access, capacity, allocation, and robustness.
Every checkpoint is initially inconclusive because figures and tables are still pending.
Support status is assigned only after the generated evidence passes the stated checks.

| step | variables used | formula/model used | generated figure/table title | theory or claim evaluated | support status |
|---|---|---|---|---|---|
| Audit reporting and spatial linkage | Municipality Match Status, Spatial Join Status, Location Resolution Status, Location Resolution Source, Network Snap Accepted, Road Edge Match Status, Road Edge Match Candidate Count | Coverage counts and explicit unmatched denominators | Data Linkage and Coverage Audit | Tests whether outage, population, facility, and road evidence can be linked without silent record loss. | inconclusive until generated |
| Construct resident and shelter demand | Estimated Outage Population, Outage Population Scenario, Per Capita Water Demand (L/person/day), Demand Scenario, Estimated Water Demand (L/day), Evacuee People, Estimated Shelter Water Demand (L/day), Shelter Demand Accounting Status | Daily mesh, shelter, municipal, and cumulative demand equations | Outage Population and Emergency Water Demand; Municipality Outage Population and Water Demand | Evaluates RQ2 and the demand component of the central question. Bounds must remain ordered, municipality totals must reconcile, and shelter demand must remain separate. | inconclusive until generated |
| Document scenario evidence | Parameter Name, Scenario Level, Parameter Value, Parameter Unit, Evidence Class, Evidence Source, Parameter Notes, Historical Capacity Only | Primary-scenario declaration and one-factor sensitivity design | Scenario Parameters and Evidence | Tests whether observed evidence, official references, and researcher-defined assumptions are distinguishable and auditable. | inconclusive until generated |
| Estimate nominal access | Demand Node ID, Water Point Node ID, Shelter Node ID, Population Age 65+, Evacuee People, Road Length (m), Network Snap Accepted, Location Resolution Status | Shortest network-distance and weighted coverage equations under road and point states | Announced Water Points and Nominal Access Coverage; Accessibility Coverage by Distance Threshold; Municipality Accessibility and Priority Gaps | Evaluates RQ3. Results must report unresolved and disconnected shares and must be labeled as a road-network proxy rather than observed walking behavior. | inconclusive until generated |
| Calculate tanker workload | Estimated Water Demand (L/day), Estimated Shelter Water Demand (L/day), Dispatch Base Node ID, Water Point Node ID, Baseline Edge Travel Time (min), Parameter Name, Scenario Level, Parameter Value, Maximum Daily Supply (m3/day), Historical Capacity Only | Feasible-trip, deliverable-volume, and required-tanker equations | Required Water Volume and Tanker Workload; Water-Point Capacity and Tanker Requirements | Evaluates RQ4. Volume and fleet results must be described as required capacity under assumptions, not actual supply gaps or realized trips. | inconclusive until generated |
| Solve resident and shelter allocation ledgers | Candidate Staging Site ID, Candidate Staging Site Name, Screened Staging Candidate, Candidate Network Eligible, Staging Demand Node ID, Candidate Dispatch Base, Dispatch Base Node ID, Water Treatment Facility Name, Matched Road Edge ID, Road Edge Match Status, Estimated Water Demand (L/day), Estimated Shelter Water Demand (L/day) | Demand-balance, access, vehicle-capacity, fleet, and lexicographic allocation model | Scenario-Based Tanker and Temporary Water-Point Allocation; Scenario-Based Priority Deployment List | Evaluates RQ1 and the placement component of RQ5. Solutions must be feasible, improve or explain failure to improve transparent baselines, and keep the two demand ledgers separate. | inconclusive until generated |
| Measure marginal returns and robustness | Estimated Outage Population, Estimated Water Demand (L/day), Demand Scenario, Parameter Name, Scenario Level, Parameter Value, Road Edge Match Status, Water Point Node ID | Protected share, total unmet water, marginal gain, deployment stability, and 162-scenario factorial comparison | Marginal Protection Gains from Additional Tankers; Scenario Performance and Robustness | Evaluates the resource-curve and robustness components of RQ5. Unstable sites or small marginal gains weaken a single preferred deployment claim. | inconclusive until generated |
| Synthesize the closed planning chain | All variables and models above | Cross-output reconciliation of demand, access, required capacity, allocation, and remaining gap | All planned figures and tables | Evaluates the central research question. The conclusion is partially supported only if outputs reconcile and remain stable enough for scenario planning; otherwise it is inconclusive or weakened. | inconclusive until generated |

### Evidence Checkpoints

- Demand passes when lower, central, and upper Estimated Outage Population remain ordered,
  municipal aggregation is internally consistent, and all missing outage observations remain
  distinguishable from reported zeros.
- Access passes when coverage denominators, unresolved Water Point Name records, unresolved
  Shelter Name records, rejected Network Snap Accepted records, and disconnected routes are
  reported for every population class and threshold.
- Workload passes when assigned demand equals delivered plus unmet water, tanker trips satisfy
  service-time and Daily Work Limit assumptions, and historical capacity is never labeled current.
- Allocation passes when every selected route satisfies access, road-state, point-state, trip,
  and Fleet Size constraints and when results are compared with nearest-point and proportional
  allocation baselines.
- Robustness passes for scenario planning only if the direction of resource gains is stable and
  priority locations do not change drastically under small assumption changes. Failure does not
  invalidate the data; it limits the result to a scenario range rather than a single deployment.

## 8. Figure and Table Plan

The planned outputs follow the demand-access-capacity-allocation-gap chain. Outputs that
depend on routing, assignment, tanker workload, optimization, protected population, or unmet
demand remain scenario results whose definitions and constraints must be specified in Sections
5-7 before generation.

### Figures

| title | what it expresses | figure type | subpanels | key variables | status |
|---|---|---|---:|---|---|
| Outage Population and Emergency Water Demand | Maps affected-population estimates and emergency-water demand at mesh and municipality support under the lower, central, and upper planning bounds, addressing the demand component of the research objective. | map | 3 | Reporting Municipality Name, Geometry, Estimated Outage Population, Estimated Water Demand (L/day), Outage Population Scenario, Demand Scenario | pending |
| Announced Water Points and Nominal Access Coverage | Maps resolved announced water points, affected demand, and nominal network coverage while explicitly representing unresolved-location sensitivity. | map | 3 | Water Point Name, Water Point Node ID, Location Resolution Status, Demand Node ID, Estimated Outage Population, Network Snap Accepted, Parameter Name, Parameter Value | pending |
| Accessibility Coverage by Distance Threshold | Compares cumulative coverage of affected residents, older residents, and shelter evacuees across the approved access-distance thresholds. | line | 3 | Estimated Outage Population, Population Age 65+, Evacuee People, Demand Node ID, Water Point Node ID, Shelter Node ID, Road Length (m), Parameter Name, Parameter Value | pending |
| Required Water Volume and Tanker Workload | Compares required daily water volume and tanker workload across demand, vehicle-capacity, trip-count, service-time, and work-hour assumptions. | heatmap | 3 | Estimated Water Demand (L/day), Estimated Shelter Water Demand (L/day), Demand Scenario, Dispatch Base Node ID, Water Point Node ID, Baseline Edge Travel Time (min), Parameter Name, Scenario Level, Parameter Value | pending |
| Scenario-Based Tanker and Temporary Water-Point Allocation | Maps tanker bases, historical refill candidates, selected temporary water points, and service areas under baseline, road-disruption, and point-failure scenarios. | map | 3 | Candidate Staging Site ID, Candidate Staging Site Name, Staging Demand Node ID, Dispatch Base Node ID, Water Treatment Facility Name, Matched Road Edge ID, Road Edge Match Status, Estimated Water Demand (L/day), Scenario Level | pending |
| Marginal Protection Gains from Additional Tankers | Shows the incremental protected-population gain and remaining unmet water requirement as the scenario fleet expands under alternative disruptions. | line | 2 | Estimated Outage Population, Estimated Water Demand (L/day), Demand Scenario, Parameter Name, Scenario Level, Parameter Value, Road Edge Match Status, Water Point Node ID | pending |

### Tables

| title | what it expresses | rows | columns | row meaning | column meaning | status |
|---|---|---:|---:|---|---|---|
| Data Linkage and Coverage Audit | Summarizes completeness and uncertainty in reporting-unit, mesh, facility, road, and network linkages. | 9 | 7 | One linkage or matching component. | Component, total records, successful records, unmatched records, coverage rate, acceptance rule, and interpretation limit. | pending |
| Scenario Parameters and Evidence | Documents official-reference and researcher-defined sensitivity assumptions used by the planning scenarios. | 35 | 7 | One parameter scenario level. | Parameter Name, Scenario Level, Parameter Value, Parameter Unit, Evidence Class, Evidence Source, and Parameter Notes. | pending |
| Municipality Outage Population and Water Demand | Reports outage-population bounds and daily water demand for the 45 municipalities plus the unmatched-mesh audit unit. | 46 | 13 | One reporting municipality or unmatched-mesh audit unit. | Outage observation, reported households, household ratio, lower, central, and upper population estimates, three daily demand levels, snapshot, and linkage status. | pending |
| Municipality Accessibility and Priority Gaps | Reports nominal access coverage and gaps for affected residents, older residents, and shelter evacuees by municipality. | 45 | 14 | One reporting municipality. | Coverage at 250, 500, and 1,000 m, uncovered affected population, older-population strict-threshold results, shelter coverage, and unresolved-location sensitivity. | pending |
| Water-Point Capacity and Tanker Requirements | Reports the water volume, trip count, and tanker fleet required at each announced point under explicit scenarios. | 36 | 15 | One announced water point, including unresolved points. | Location status, operating schedule, allocation limit, assigned demand, required capacity, trips, vehicles, and scenario identifiers. | pending |
| Scenario-Based Priority Deployment List | Provides the highest-priority temporary water-point, tanker-base, refill-candidate, and service-area combinations. | 20 | 14 | One priority deployment location. | Location, municipality, served population, required water, dispatch base, refill candidate, travel requirement, vehicles, trips, road state, and remaining gap. | pending |
| Scenario Performance and Robustness | Compares allocation outcomes across outage-population, demand, fleet, road, and point-state combinations. | 162 | 10 | One complete scenario combination. | Scenario settings, protected-population share, unmet water, access burden, sites used, and route feasibility. | pending |

# Atlas of Intelligence: Information Architecture Audit

**Scope:** Read-only review of the v3.0.0 package, imported SQLite release and current React frontend. This audit creates only this report and the mapping appendix; it does not alter application code, curriculum, schema or database contents.

## 1. Executive findings

- The package is curriculum release **3.0.0**, schema **1.0.0-draft**, status **curriculum_release_candidate**. Its 334 stable Topic IDs have 5 Tracks, 17 Phase placements, 534 prerequisite edges, 17 Related Topic links, 1,002 objectives, 8 migration entries, 89 learner records and 9 evidence records. Structural database counts match. The current database has 95 progress rows: six additional explicit assessments beyond the ZIP snapshot.
- All Topics have one Phase placement; 128 have more than one Track membership. Track totals overlap and are not additive. There is no Track-to-Phase parent-child structure.
- Tracks and Phases provide useful navigation axes, but source records have titles only, not explicit purposes, boundaries or milestones. The proposed three-layer structure below is a presentation mapping, not source ontology.
- Computer Science and Engineering are distinct Tracks (34 and 90 memberships) with no shared Topic membership. The package does not explain their boundary or why they are separate. Prerequisite edges connect their areas. Do not merge or split them without curriculum-author interpretation.
- Prerequisites are formal learning dependencies; Related Topics are distinct conceptual links. Phase placement and pathway values are not prerequisite semantics.
- The UI can evolve as coordinated views of one Atlas: Roadmap for source structure, Explore for the Topic index, Topic detail for relationships and Progress for the learner overlay. The Progress view must not become the curriculum's intellectual map.
- Educational content is first-pass. The package explicitly says content_draft concerns maturity, not structural validity. Graph checks passed, but first-pass dependency judgments are not external expert certification.

## 2. Existing curriculum structure

### Package and integrity

The ZIP contains curriculum_registry.json, dependency_registry.json, learner_progress.json, validation_report.json, README.md and CODEX_HANDOFF.md. Validation reports 334 unique active Topics, zero duplicate IDs, zero pending dependency reviews, zero unresolved dependency references, zero duplicate edges, an acyclic union graph and 534 prerequisite edges. Eight Topics have empty prerequisite groups; those are explicit reviewed no-formal-prerequisite decisions. Every Topic has three objectives. Optional exercise, project and resource arrays are intentionally empty. SQLite structural counts match the package. The ZIP's learner snapshot contains 89 progress records; the current local database contains 95 for its one learner, including six explicit records not present in the original package snapshot (AD-005, AD-007, DM-001, DM-002, DM-003 and DSA-011). This is consistent with later learner activity and is not a curriculum import mismatch. The ZIP says 245 Topics were unassessed at reconstruction; with six additional current records, the current database leaves 239 Topics without a progress row.

### Tracks

| Track | ID | Membership count | Source boundary/purpose |
|---|---|---:|---|
| Computer Science | TR-CS | 34 | Title only; no descriptive definition |
| Mathematics | TR-MATH | 111 | Title only; no descriptive definition |
| Engineering & Systems | TR-ENG | 90 | Title only; no descriptive definition |
| Machine Learning | TR-ML | 200 | Title only; no descriptive definition |
| Intelligence & Advanced AI | TR-AI | 48 | Title only; no descriptive definition |

There are 483 membership rows. Each Topic may be in several Tracks.

### Phases

| Phase | ID | Placement count |
|---|---|---:|
| Computational and Mathematical Foundations | PH00 | 8 |
| Programming and Software Design | PH01 | 22 |
| Discrete Mathematics | PH02 | 10 |
| Data Structures and Algorithms | PH03 | 12 |
| Linear Algebra | PH04 | 21 |
| Calculus and Multivariable Calculus | PH05 | 15 |
| Numerical Computing and Autodiff | PH06 | 39 |
| Probability and Statistics | PH07 | 23 |
| Optimization | PH08 | 13 |
| Classical Machine Learning | PH09 | 31 |
| Neural Networks and Backpropagation | PH10 | 20 |
| Deep Learning and Representation Learning | PH11 | 13 |
| Transformers and Generative AI | PH12 | 14 |
| LLM Systems and Inference | PH13 | 26 |
| ML Engineering and Systems | PH14 | 19 |
| Reinforcement Learning and Agents | PH15 | 24 |
| Advanced Intelligence and Research | PH16 | 24 |

Counts sum to 334 because each Topic has exactly one current placement. Phase number/order may suggest sequence, but source says Phase is not a hard readiness gate and does not define it as completion milestone. PH06 includes Engineering, Mathematics and ML memberships; PH13 has Engineering and ML; PH15 has ML and AI; PH16 has AI, ML and Engineering. These are placement clusters, not Track children.

### Topic record

Each of 334 Topics has stable ID, title, description, Track IDs, Phase ID, pathway, prerequisite groups, Related Topic IDs, three objectives, learning target, depth frontier, revisit triggers, priority and rationale, registry/dependency review status and optional content ID arrays. See the complete source/proposal side-by-side appendix: [reports/atlas_topic_mapping_appendix.json](reports/atlas_topic_mapping_appendix.json).

## 3. Computer Science versus Engineering

**Source facts:** TR-CS memberships are in PH01 Programming and Software Design (22) and PH03 Data Structures and Algorithms (12). TR-ENG is concentrated in PH06 (39), PH13 (20), PH14 (19) and PH16 (12). There are zero Topics with both TR-CS and TR-ENG membership.

**What the organization suggests, not a formal definition:** CS emphasizes general programming, software design, data structures and algorithms. Engineering & Systems emphasizes numerical implementations, inference/retrieval, ML operations and system/research practice. Their concerns meet in software used to build and operate learning systems.

**Graph evidence:** CS-006 Collections and data manipulation precedes ENG-004 NumPy arrays. CS-019 References, aliasing and shared mutable state and CS-020 Memory allocation and object lifetime connect to ENG-009 memory work. CS-017 Software design, interfaces and responsibility precedes SYS-012 Inference APIs and serving. These are curriculum-defined prerequisites. Across the full graph, 81 prerequisite edges connect endpoints with disjoint Track memberships.

**Undocumented:** the package supplies no Track descriptions, inclusion/exclusion rules, rationale for separating CS and Engineering, or shared Topic bridge between them. The evidence supports cross-area navigation, not merging or splitting the Tracks.

## 4. Cross-track and cross-disciplinary relationships

Examples supported by prerequisite edges:

- LA-001 Vectors and LA-002 Vector spaces connect mathematical foundations to ML-007 Linear models.
- CAL-004 Chain rule and composition and CAL-007 Partial derivatives connect calculus to NN-007 Backpropagation and gradient computation.
- CS-001 Computational thinking and decomposition and CS-006 Collections and data manipulation lead into ML Topics.
- CS-005 Modules, imports and namespaces leads into SYS-002 Environments and dependency management.
- ML-001 Classical machine-learning foundations, ML-012 and PROB-015 connect to AI-010, AI-011 and AI-012.
- O-002 Gradient descent has 12 direct dependents; ML-003 Datasets, samples, features and labels has 11. These are useful navigation junctions, not importance rankings.

The 17 Related links form a separate, relatively sparse layer. Examples: CAL-004 → AD-003 and NN-007; AD-004 → NN-007 and PT-010; DL-002 → IR-003 and RAG-003; LLM-001 → TRF-014 and RAG-006; RES-005 → ML-011, LLM-009 and RAG-007. Preserve stored directionality; reciprocity is not guaranteed. Never treat these as dependencies.

Pathway values are core (212), supporting (76), optional (38) and exploratory (8). Priority and depth are also separate dimensions. Source language calls a route a suggestion, not a gate.

## 5. Proposed high/middle/low presentation structure

| Layer | Proposed mapping | Rationale and caveat |
|---|---|---|
| High: Mathematical foundations | TR-MATH, editorial label | Track membership; some Topics also have applied Phase placement |
| High: Computation and software | TR-CS, editorial paraphrase | Fits title and membership, but boundary with Engineering is unresolved |
| High: Engineering and systems | TR-ENG | Near-source title; overlaps ML and AI |
| High: Machine learning | TR-ML | Near-source title; broadest/most overlapping Track |
| High: Intelligence and research | TR-AI, editorial paraphrase | Does not imply every Topic is research |
| Middle: Knowledge field | Source Phase title | Display as separate placement facet, not nested under one high territory |
| Low: Idea | Source Topic ID/title | Stable ID for traceability; retain source relationships |

**Mapping rule for the appendix:** a single Track yields mapped (206); multiple Track memberships yield cross-cutting (128). The high proposal retains every source membership; the middle field is the Topic's source Phase. No Topic lacks either field, so there are zero structurally unplaced/unresolved Topics. This is not proof of editorial certainty: CS/Engineering boundaries and Phase ontology require human review. “Others” is not justified by the current data. No source membership is changed.

## 6. Journey and candidate landmarks

Candidates are entry points and graph junctions, not invented milestones:

- Entry points with reviewed no-formal-prerequisite decisions include MATH-001 Arithmetic and numerical operations; CS-001 Computational thinking and decomposition; CS-002 Python syntax, types and expressions; SYS-001 Version control with Git; AI-001 Definitions and theories of intelligence.
- Mathematics into ML: LA-001 → LA-003 Matrices and matrix operations → ML-007 Linear models.
- Calculus into neural networks: CAL-004/CAL-007 → NN-007.
- Computing into implementation: CS-006 → ENG-004; CS-005 → SYS-002.
- Learning into intelligence: ML-001, ML-012 and PROB-015 connect to AI-010/011/012.

Render the actual AND-within-group / OR-between-group structure when showing paths. A learner journey should overlay real learner records on this map; do not claim completion from source importance. The ZIP snapshot is a partial reconstruction with 245 Topics unassessed and no confidence values. The current database has later assessments on six of those Topics, including confidence values; treat it as the present personal record, not as identical to the source snapshot. Learner data was not modified during this audit.

## 7. Vocabulary

**Current terms:** Atlas of Intelligence and Curriculum atlas can coexist as product name and release context. Roadmap can imply a required sequence; Field index and Personal record are understandable but use a different metaphor. Lines of inquiry and Phases as a horizon fit non-linearity but are decorative unless their relation to source fields is explained. Ideas in motion and Established knowledge are evocative but should not replace exact progress labels. “Unexplored territory” overstates what is known about a missing record.

**Proposed system:** Atlas (product), Release (edition context), Territory (explicitly a presentation grouping), Field (Phase placement), Topic (source entity), Connections (separate prerequisite and Related links), Progress/Learning record (learner overlay). Use exact state labels: Solid, Learning, Practicing, Revisit, Not started and Unassessed. Use poetic subtitles only as supporting copy.

## 8. Visual semantics (palette deferred)

- Learning state: exact text label plus distinct icon/shape; Solid, Learning, Practicing, Revisit, Not started and Unassessed must remain distinguishable without color. Unassessed should mean no record; Not started is an explicit value.
- Confidence: separate scale and control; it does not affect status or readiness.
- Prerequisites: directional solid connector or grouped list; AND within a group, OR between groups; readiness informational.
- Related Topics: separate section and lighter/dashed or non-directional connector; never join prerequisite evaluation.
- Territory identity: optional pattern/accent independent of state colors. Multi-membership Topics retain all affiliations.
- Phase placement: a labeled positional/facet treatment, never a dependency arrow or learner state.

## 9. Current application assessment

AppShell supplies release and learner context plus shared navigation. Roadmap gives a summary and separate Track/Phase browsing; Explore provides search and Track/Phase/status filters; Topic detail combines content, assessment, readiness, prerequisites, Related links and downstream links; Progress is a learner-specific view. Reusable pieces include TopicLink, ProgressEditor, state views, Atlas context and typed API client.

- Roadmap's Track and Phase lists correctly preserve separate source axes; the route name “Roadmap” can imply sequence.
- Explore is a useful 334-Topic index. It should keep progressive navigation/search rather than present every Topic as equally important.
- Topic detail is the best home for fine-grained content and relationship explanations.
- Progress is not duplicate curriculum hierarchy; it should remain an assessment overlay and use exact state terms.
- Track/Phase/status labels recur across views. Use consistent semantic tokens and counts; keep learner summaries visually secondary to curriculum structure.
- Cross-axis Track/Phase membership and cross-track prerequisites are not prominent in the current overview.
- The route illustration and orbit mark are atmospheric, not data-backed routes. They must not be read as factual pathways.
- Current editorial typography, restrained color and whitespace support the atlas direction. Coordinate the pages as views into one release-scoped map rather than nesting Track and Phase.

## 10. Decisions requiring human interpretation

1. Define Computer Science and Engineering boundaries and why they are separate.
2. State whether Phases mean subject placement, intended sequence, or both.
3. Approve verbatim Track labels versus editorial territory names.
4. Decide whether multi-Track memberships are equal affiliations or have a primary display affiliation.
5. Define whether Related Topic links should be reciprocal.
6. Decide the display weight of pathway, priority, depth and registry status.
7. Set educational review gates for first-pass descriptions, objectives and prerequisite decisions.
8. Define release-revision presentation and historical handling for renames, moves, retirement and splits; do not automatically transfer learner state.
9. Keep historical roadmap evidence separate from current learner assessment. It is context, not a present-state authority. Keep the package's 89-record snapshot distinct from the database's 95-row current record.

## 11. Method

The appendix includes all 334 Topics with source fields separate from proposal fields, retaining descriptions, memberships, placement, prerequisite groups, Related IDs and objectives. Package counts were compared with the imported database. No data or application writes were made.

# Expected Output — Software Engineer

## Format
Output is an HTML artifact page. A 2–3 line text summary is printed in chat before the artifact. No company names appear anywhere.

## Chat summary
> Analyzed **3** postings (0 could not be opened). With only 3 postings, gap rankings may not reflect broader market demand.
> Top gaps: Kubernetes and Go (required by 2 of 3 postings), Kafka (2 postings).
> Strengths: distributed systems, SQL/NoSQL databases, and cloud platforms appear in 2 of 3 postings.

## Wording gaps to verify

These are skills the resume demonstrates but doesn't name with the posting's keyword.

| Posting Keyword | Resume Evidence | Suggested Rewrite |
|----------------|-----------------|-------------------|
| Message queues | "built event-driven data pipelines using AWS Lambda and SQS" | "Built event-driven data pipelines using AWS Lambda and **SQS message queues**, processing 2M events/day" |
| Automated tests | "Implemented CI/CD pipelines using Jenkins and GitHub Actions, cutting release cycles…" | "Implemented CI/CD pipelines with **automated test suites** using Jenkins and GitHub Actions…" |
| Distributed systems | "Designed and deployed a multi-region API gateway…" + "Led migration… to microservices" | "Designed and deployed a **distributed** multi-region API gateway serving 50K requests/minute…" |

## True gaps to verify

| Rank | Skill | Category | Postings | Level | Score | Evidence | Next Step |
|------|-------|----------|----------|-------|-------|----------|-----------|
| 1 | Kubernetes | Tools / Software | 2 / 3 | Required | 2.0 | "Experience with Kubernetes and container orchestration" | Complete CKA certification or deploy a side project on minikube |
| 2 | Go | Tools / Software | 2 / 3 | Required | 2.0 | "Strong proficiency in Go or Java" | Build a small CLI tool or REST API in Go; add to GitHub |
| 3 | Kafka | Tools / Software | 2 / 3 | Mixed | 1.5 | "message queues (Kafka, RabbitMQ, or SQS)" | Confluent's free Kafka Fundamentals course; build a producer/consumer demo |
| 4 | Rust | Tools / Software | 1 / 3 | Required | 1.0 | "Proficiency in Python, Go, or Rust" | Work through Rustlings exercises; build a small systems tool |
| 5 | gRPC | Tools / Software | 1 / 3 | Preferred | 0.5 | "Experience with gRPC" | Add a gRPC endpoint to an existing project alongside REST |
| 6 | Service mesh (Istio / Linkerd) | Tools / Software | 1 / 3 | Preferred | 0.5 | "Familiarity with service mesh (Istio, Linkerd)" | Set up Istio on a local K8s cluster after learning Kubernetes |
| 7 | ArgoCD / Flux (GitOps) | Tools / Software | 1 / 3 | Preferred | 0.5 | "Familiarity with GitOps practices (ArgoCD, Flux)" | Deploy an app with ArgoCD after learning Kubernetes |
| 8 | Apache Flink | Tools / Software | 1 / 3 | Preferred | 0.5 | "Experience with Apache Kafka or Apache Flink" | Apache Flink Playground tutorials with a sample streaming job |
| 9 | eBPF / kernel networking | Technical Skills | 1 / 3 | Preferred | 0.5 | "Experience with eBPF or Linux kernel networking" | Isovalent's free eBPF labs |
| 10 | Cloud cost optimization | Technical Skills | 1 / 3 | Preferred | 0.5 | "Knowledge of cost optimization for cloud infrastructure" | AWS Well-Architected Labs cost optimization pillar |
| 11 | Next.js | Tools / Software | 1 / 3 | Preferred | 0.5 | "Experience with Next.js or similar SSR frameworks" | Convert existing React project to Next.js |
| 12 | Fintech domain | Domain Knowledge | 1 / 3 | Preferred | 0.5 | "Experience with financial systems or fintech" | Target a fintech side project or open-source contribution |
| 13 | Open-source contributions | Technical Skills | 1 / 3 | Preferred | 0.5 | "Contributions to open-source projects" | Contribute to a project using one of your gap skills (Go, K8s ecosystem) |

Scoring notes:
- Kubernetes: required × 1.0 in Posting 1 + required × 1.0 in Posting 2 = 2.0
- Go: required × 1.0 in Posting 1 + required × 1.0 in Posting 2 = 2.0
- Kafka: required × 1.0 in Posting 1 + preferred × 0.5 in Posting 2 = 1.5

## Partial matches to verify

| Skill Asked For | Resume Has | Expected Match | Postings |
|-----------------|-----------|----------------|----------|
| Prometheus / Grafana | Datadog | Partial — different observability tools | 1 / 3 |
| RabbitMQ | SQS | Partial — different message broker | 1 / 3 |
| Sentry | Datadog | Partial — different monitoring tool | 1 / 3 |
| Pulumi / CloudFormation | Terraform | Partial — different IaC tools | 1 / 3 |
| GCP | AWS, Azure | Partial — different cloud provider | 1 / 3 |
| Apache Flink | Lambda + SQS pipelines | Partial — stream processing, different tool | 1 / 3 |

## Experience & seniority check to verify

| Role | Required Experience | Resume Experience | Status |
|------|-------------------|-------------------|--------|
| Sr Backend Engineer (Posting 1) | 5+ years | ~4.5 years (Jan 2022 + Jun 2019) | Amber — slightly under |
| Platform Engineer (Posting 2) | 3+ years production infra | ~4.5 years | Green |
| Full-Stack Engineer (Posting 3) | 3+ years full-stack | ~4.5 years | Green |

## Top priorities to verify (true gaps only)

1. Kubernetes — required by 2/3 postings; Docker experience makes it a natural next step.
2. Go — required by 2/3 postings; fast to pick up with Java background.
3. Kafka — 2/3 postings; SQS experience provides foundation.
4. gRPC — pairs with existing REST and microservices skills.
5. GitOps (ArgoCD / Flux) — complements Terraform and CI/CD experience.

## Strongest skills to verify

- Distributed systems: 2 / 3
- SQL / relational databases: 2 / 3
- NoSQL databases: 2 / 3
- Docker / containers: 2 / 3
- Cloud platforms (AWS / Azure): 2 / 3
- Datadog / observability: 2 / 3

## Checks

- [ ] Go appears as a true gap, not a match (resume has Java/Python but not Go)
- [ ] Kubernetes appears as a true gap (not listed on resume)
- [ ] Terraform is a full match, not a gap
- [ ] Datadog is a full match; Prometheus/Grafana are partial matches
- [ ] SQS is a full match; "message queues" is a wording gap (resume has SQS but doesn't use the phrase)
- [ ] Wording gap rewrites never fabricate skills — only rephrase existing bullets
- [ ] Experience check flags Posting 1 as amber (4.5 yrs vs 5+ required)
- [ ] No company names appear anywhere in the artifact
- [ ] Small-sample warning present (only 3 postings)
- [ ] Priority cards drawn only from true gaps
- [ ] Every true gap has a posting evidence quote
- [ ] Every true gap has a concrete next step

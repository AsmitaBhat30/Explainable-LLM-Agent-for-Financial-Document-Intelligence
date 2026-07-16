# Explainable-LLM-Agent-for-Financial-Document-Intelligence
An AI system that analyzes financial documents, answers regulatory questions, and produces traceable explanations suitable for risk and compliance teams.

```mermaid
flowchart TD

    subgraph SRC["Financial Documents"]
        direction LR
        s1["SEC EDGAR 10-K"]
        s2["MiFID II · PSD2"]
        s3["GDPR · CRR · BaFin"]
        s4["Basel III · ECB Manual"]
    end

    subgraph ING["Ingestion"]
        i1["PDF Parser"] --> i2["Document Processor"] --> i3[("data/parsed")]
    end

    subgraph TRF["Transformation"]
        t1["Chunker 512tok · 50 overlap"] --> t2["Embedder all-MiniLM-L6-v2"] --> t3[("FAISS IVF Index")]
    end

    subgraph API["FastAPI :8000"]
        a1["JWT Auth"] --> a2["SSE Streaming Endpoint"]
    end

    subgraph AGT["Agent Pipeline"]
        direction LR
        ag1["RetrieverAgent"] --> ag2["ComplianceAgent"] --> ag3["ExplanationAgent"]
    end

    subgraph OUT["Response"]
        o1["Cited Answer"] & o2["Compliance Flags"] & o3["Explanation Trace"]
    end

    SRC --> ING --> TRF
    t3 -->|"top-k chunks"| ag1
    USR(["Client"]) -->|"Bearer JWT"| API
    a2 --> AGT
    ag3 --> OUT
    OUT --> a2 --> USR
    AGT -.->|"log_decision()"| MON[["Audit Logger · Prometheus"]]
```
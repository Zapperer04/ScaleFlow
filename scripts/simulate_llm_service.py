import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from services.llm_service import generate_answer

# Mock the retrieved chunks for testing
chunks = [
    {
        "chunk_index": 0,
        "chunk_text": 'ScaleFlow|Flask, React, PostgreSQL, Redis, Qdrant, Docker\n Built a distributed AI document intelligence platform for large-scale document processing and retrieval workflows.\n Designed a fault-tolerant orchestration engine with lease-based scheduling, worker recovery, fencing tokens, and\nautomated queue healing.\n Implemented a 6-stage RAG pipeline comprising document parsing, OCR fallback, chunking, embedding\ngeneration, vector retrieval, and summarization.\nBhoomi Mitra(Patent Published)|HTML, CSS, JavaScript, Flask, SQLAlchemy, JWT\n Developed a multilingual farmer assistance and crop marketplace platform supporting role-based access for farmers\nand contractors.\n Built 10+ REST APIs enabling crop listing, negotiations, messaging, authentication, and marketplace operations.\n Implemented a multilingual web platform and selection-based chatbot supporting 12 languages, providing 4+\nagricultural services including weather forecasts, MSP information, crop advisories, and government scheme\nrecommendations.\n Contributed to a Government of India published patent based on the Bhoomi Mitra platform.\nLinkF ort|Flask, React, PostgreSQL, Redis, XGBoost, Docker\n Developed a URL shortening and phishing detection platform featuring a React dashboard and Flask backend with\n16 REST API endpoints.\n Designed a multi-layer phishing detection framework integrating rule-based security checks, an XGBoost classifier\ntrained on 15 engineered URL features, and VirusTotal API verification for malicious URL detection.\n Implemented JWT authentication, Redis caching, background worker processing, analytics tracking, and secure\nURL management workflows.\n Containerized the application using Docker and configured production-ready deployment infrastructure with\nautomated validation and testing pipelines.'
    },
    {
        "chunk_index": 2,
        "chunk_text": 'Languages: C, C++, Java, Python, JavaScript, SQL\nF rameworks & T ools: Flask, React, REST APIs, Git, GitHub, Docker\nDatabases: PostgreSQL, SQLAlchemy, Redis, Qdrant\nAI/ML: Machine Learning, Deep Learning, Natural Language Processing, RAG, Embeddings, Vector Search,\nReranking, XGBoost\nCoursework: DSA, OOP, DBMS, Operating Systems, Computer Networks'
    },
    {
        "chunk_index": 3,
        "chunk_text": 'Industry T rainee  PwC Launchpad ProgramJan 2026  Present\nPricewaterhouseCoopers (PwC) Remote\n Undergoing structured training in Salesforce ecosystem, CRM fundamentals, enterprise cloud solutions, and digital\ntransformation workflows.  Learning Generative AI concepts, business process automation, and enterprise application development practices\nthrough guided industry training. UI/UX InternJune 2025  July 2025\nVodafone Idea PVT. LTD. Mumbai, India\n Proposed UI/UX enhancements for recharge journeys and recommendation workflows within the Vi mobile\napplication.  Redesigned interface layouts and user flows to improve discoverability, accessibility, and user engagement across key\nscreens.  Gained exposure to telecom analytics use cases including detractor-based churn prediction, market basket analysis,\nand regression-based recommendation.'
    }
]

print("=== RUNNING INTERNSHIPS QUERY ===")
ans, provider, status = generate_answer("What internships has the candidate completed?", chunks)
print("Answer:\n", ans)
print("Provider:", provider, "Status:", status)

print("\n=== RUNNING PROJECTS QUERY ===")
ans, provider, status = generate_answer("What projects are listed?", chunks)
print("Answer:\n", ans)
print("Provider:", provider, "Status:", status)

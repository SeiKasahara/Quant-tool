from datetime import datetime, timedelta

# Mock data for testing when feeds are unavailable
MOCK_ARTICLES = [
    {
        "title": "Apple (AAPL) Raises Full-Year Guidance After Strong iPhone Sales",
        "url": "https://example.com/apple-guidance-up",
        "published": datetime.now() - timedelta(hours=1),
        "source": "DJ",
        "content": """Apple Inc. (AAPL) announced today that it is raising its full-year revenue guidance 
        following stronger-than-expected iPhone 15 sales in the fourth quarter. The company now expects 
        revenue growth of 8-10% for the fiscal year, up from previous guidance of 5-7%. CEO Tim Cook 
        cited strong demand in emerging markets and the success of new AI features as key drivers. 
        The stock jumped 3% in after-hours trading following the announcement."""
    },
    {
        "title": "Tesla (TSLA) Beats Earnings Estimates, Announces New Product Launch",
        "url": "https://example.com/tesla-earnings",
        "published": datetime.now() - timedelta(hours=2),
        "source": "NASDAQ",
        "content": """Tesla Inc. (TSLA) reported quarterly earnings that exceeded Wall Street estimates, 
        with earnings per share of $0.85 versus expectations of $0.73. The electric vehicle maker also 
        unveiled plans for a new affordable model targeting the $25,000 price point. Production is 
        expected to begin in late 2024. Revenue grew 15% year-over-year to $25.2 billion."""
    },
    {
        "title": "Microsoft (MSFT) Announces Major Acquisition in AI Space",
        "url": "https://example.com/microsoft-acquisition",
        "published": datetime.now() - timedelta(hours=3),
        "source": "Reuters",
        "content": """Microsoft Corporation (MSFT) has agreed to acquire AI startup DeepMind Technologies 
        for $12 billion, marking its largest acquisition in the artificial intelligence sector. The deal 
        is expected to close in Q2 2024, pending regulatory approval. This acquisition will strengthen 
        Microsoft's position in enterprise AI solutions and complement its existing Azure AI services."""
    },
    {
        "title": "Amazon (AMZN) Faces Regulatory Investigation Over Market Practices",
        "url": "https://example.com/amazon-probe",
        "published": datetime.now() - timedelta(hours=4),
        "source": "WSJ",
        "content": """Amazon.com Inc. (AMZN) is facing a new regulatory probe from the FTC regarding its 
        marketplace practices and treatment of third-party sellers. The investigation focuses on whether 
        Amazon gives preferential treatment to its own products. The company stated it will cooperate 
        fully with regulators. Amazon shares fell 2% in pre-market trading."""
    },
    {
        "title": "NVIDIA (NVDA) Announces Increased Dividend and Share Buyback Program",
        "url": "https://example.com/nvidia-dividend",
        "published": datetime.now() - timedelta(hours=5),
        "source": "Bloomberg",
        "content": """NVIDIA Corporation (NVDA) announced a 15% increase in its quarterly dividend and 
        authorized a new $25 billion share buyback program. The semiconductor giant's strong cash flow 
        from AI chip sales has enabled increased returns to shareholders. The dividend will increase 
        to $0.04 per share, payable next quarter."""
    }
]

# service_catalog.py
# Betrayal DeepDive Freelance Empire - Service Catalog

SERVICES = {
    "starter": [
        {
            "id": "S1",
            "name": "SEO Blog Article",
            "description": "1000-1500 word SEO-optimized blog article on any topic",
            "price_usd": 25,
            "delivery_days": 2,
            "revisions": 2
        },
        {
            "id": "S2",
            "name": "YouTube Script",
            "description": "5-10 minute engaging YouTube script with hook, body, CTA",
            "price_usd": 35,
            "delivery_days": 2,
            "revisions": 2
        },
        {
            "id": "S3",
            "name": "Social Media Pack (7 days)",
            "description": "7 days of social media captions for Instagram/Twitter/Facebook",
            "price_usd": 30,
            "delivery_days": 3,
            "revisions": 2
        },
        {
            "id": "S4",
            "name": "Product Description Pack",
            "description": "10 SEO product descriptions for ecommerce stores",
            "price_usd": 40,
            "delivery_days": 2,
            "revisions": 2
        },
        {
            "id": "S5",
            "name": "Email Newsletter",
            "description": "One professional email newsletter with subject line optimization",
            "price_usd": 25,
            "delivery_days": 1,
            "revisions": 2
        }
    ],
    "professional": [
        {
            "id": "P1",
            "name": "YouTube Automation Script Pack",
            "description": "5 fully researched YouTube scripts with SEO titles, descriptions, tags",
            "price_usd": 150,
            "delivery_days": 5,
            "revisions": 3
        },
        {
            "id": "P2",
            "name": "Intelligence Report",
            "description": "Deep research report on any industry, competitor, or market trend",
            "price_usd": 199,
            "delivery_days": 5,
            "revisions": 3
        },
        {
            "id": "P3",
            "name": "30-Day Social Media Strategy",
            "description": "Complete 30-day content calendar with captions, hashtags, posting schedule",
            "price_usd": 175,
            "delivery_days": 7,
            "revisions": 3
        },
        {
            "id": "P4",
            "name": "Website Content Pack",
            "description": "Home, About, Services, Contact pages + 3 blog posts",
            "price_usd": 250,
            "delivery_days": 7,
            "revisions": 3
        },
        {
            "id": "P5",
            "name": "AI Chatbot Setup Guide",
            "description": "Custom AI chatbot setup for your business with prompts and workflows",
            "price_usd": 299,
            "delivery_days": 7,
            "revisions": 3
        }
    ],
    "premium": [
        {
            "id": "PR1",
            "name": "Full YouTube Channel Setup",
            "description": "Complete channel strategy, 10 scripts, SEO optimization, thumbnail briefs",
            "price_usd": 499,
            "delivery_days": 14,
            "revisions": 5
        },
        {
            "id": "PR2",
            "name": "Content Empire Package",
            "description": "60-day content strategy across YouTube, Instagram, Blog with full scripts",
            "price_usd": 799,
            "delivery_days": 14,
            "revisions": 5
        },
        {
            "id": "PR3",
            "name": "Business Intelligence Suite",
            "description": "Full competitor analysis, market research, growth strategy report",
            "price_usd": 599,
            "delivery_days": 10,
            "revisions": 5
        },
        {
            "id": "PR4",
            "name": "AI Automation Consulting",
            "description": "1-hour strategy call + full automation blueprint for your business",
            "price_usd": 999,
            "delivery_days": 7,
            "revisions": "Unlimited"
        }
    ]
}

def get_service_by_id(service_id):
    for tier in SERVICES.values():
        for service in tier:
            if service["id"] == service_id:
                return service
    return None

def list_all_services():
    all_services = []
    for tier_name, services in SERVICES.items():
        for service in services:
            service["tier"] = tier_name
            all_services.append(service)
    return all_services

def get_price_inr(price_usd, exchange_rate=83):
    return price_usd * exchange_rate

if __name__ == "__main__":
    print("=== BETRAYAL DEEPDIVE FREELANCE SERVICES ===\n")
    for tier, services in SERVICES.items():
        print(f"\n{'='*40}")
        print(f"TIER: {tier.upper()}")
        print(f"{'='*40}")
        for s in services:
            inr = get_price_inr(s['price_usd'])
            print(f"\n[{s['id']}] {s['name']}")
            print(f"Price: ${s['price_usd']} USD (₹{inr:,} INR)")
            print(f"Delivery: {s['delivery_days']} days | Revisions: {s['revisions']}")
            print(f"Description: {s['description']}")

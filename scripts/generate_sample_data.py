"""
Sample dataset generator for testing GraphRAG system
Creates realistic Tech & AI news articles
"""
import pandas as pd
from datetime import datetime, timedelta
import random
from pathlib import Path


def generate_sample_dataset(num_articles: int = 50) -> pd.DataFrame:
    """
    Generate sample tech news articles
    
    Creates articles about investments, partnerships, and collaborations
    """
    
    companies = [
        "Microsoft", "Google", "Meta", "Amazon", "Apple", "OpenAI",
        "Nvidia", "Intel", "AMD", "Tesla", "Anthropic", "Cohere",
        "Hugging Face", "Stability AI", "Salesforce", "Oracle"
    ]
    
    templates = [
        # Investment templates
        {
            "type": "investment",
            "template": "{company1} announced a ${amount} billion investment in {company2}, marking a significant milestone in the AI industry. The investment will help {company2} expand its operations and develop cutting-edge technology.",
            "title": "{company1} Invests ${amount}B in {company2}"
        },
        # Partnership templates
        {
            "type": "partnership",
            "template": "{company1} and {company2} have formed a strategic partnership to collaborate on {tech} development. This partnership aims to accelerate innovation in artificial intelligence and bring new products to market.",
            "title": "{company1} Partners with {company2} on {tech}"
        },
        # Acquisition templates
        {
            "type": "acquisition",
            "template": "{company1} has acquired {company2} for ${amount} billion. The acquisition will strengthen {company1}'s position in the AI market and provide access to {company2}'s advanced technology and talent.",
            "title": "{company1} Acquires {company2} for ${amount}B"
        },
        # Product launch templates
        {
            "type": "product",
            "template": "{company1} today launched {product}, a new {tech} platform designed to revolutionize how businesses use artificial intelligence. The platform features advanced capabilities and seamless integration.",
            "title": "{company1} Launches {product} Platform"
        },
        # Collaboration templates
        {
            "type": "collaboration",
            "template": "{company1}, {company2}, and {company3} announced a joint collaboration to advance {tech} research. The three companies will pool resources and share expertise to tackle complex challenges in AI development.",
            "title": "Major Collaboration: {company1}, {company2}, {company3} Unite on {tech}"
        }
    ]
    
    technologies = [
        "AI", "machine learning", "large language models", "computer vision",
        "natural language processing", "GPU technology", "cloud computing",
        "robotics", "autonomous systems", "neural networks"
    ]
    
    products = [
        "GPT-5", "Claude Pro", "Gemini Advanced", "LLaMA 3", "Stable Diffusion 3",
        "H100 GPU", "AI Studio", "AutoML", "Vision API", "Speech AI"
    ]
    
    sources = [
        "TechCrunch", "VentureBeat", "The Verge", "Wired", "Reuters",
        "Bloomberg Technology", "CNBC", "TechRadar", "ZDNet"
    ]
    
    articles = []
    start_date = datetime(2023, 1, 1)
    
    for i in range(num_articles):
        # Select random template
        template_data = random.choice(templates)
        
        # Generate article based on type
        if template_data["type"] == "collaboration":
            company1, company2, company3 = random.sample(companies, 3)
            tech = random.choice(technologies)
            content = template_data["template"].format(
                company1=company1,
                company2=company2,
                company3=company3,
                tech=tech
            )
            title = template_data["title"].format(
                company1=company1,
                company2=company2,
                company3=company3,
                tech=tech
            )
        elif template_data["type"] == "product":
            company1 = random.choice(companies)
            product = random.choice(products)
            tech = random.choice(technologies)
            content = template_data["template"].format(
                company1=company1,
                product=product,
                tech=tech
            )
            title = template_data["title"].format(
                company1=company1,
                product=product
            )
        else:
            company1, company2 = random.sample(companies, 2)
            amount = random.choice([1, 2, 5, 10, 15, 20])
            tech = random.choice(technologies)
            content = template_data["template"].format(
                company1=company1,
                company2=company2,
                amount=amount,
                tech=tech
            )
            title = template_data["title"].format(
                company1=company1,
                company2=company2,
                amount=amount,
                tech=tech
            )
        
        # Generate date
        days_offset = random.randint(0, 730)  # 2 years
        article_date = start_date + timedelta(days=days_offset)
        
        article = {
            "title": title,
            "content": content,
            "source": random.choice(sources),
            "date": article_date.strftime("%Y-%m-%d"),
            "url": f"https://example.com/article-{i+1}"
        }
        
        articles.append(article)
    
    df = pd.DataFrame(articles)
    return df


def main():
    """Generate and save sample dataset"""
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Generate sample dataset
    print("Generating sample tech news dataset...")
    df = generate_sample_dataset(num_articles=100)
    
    # Save to CSV
    output_path = data_dir / "sample_tech_news.csv"
    df.to_csv(output_path, index=False)
    
    print(f"✓ Generated {len(df)} sample articles")
    print(f"✓ Saved to {output_path}")
    print(f"\nSample articles:")
    print(df[["title", "source", "date"]].head(10).to_string())


if __name__ == "__main__":
    main()
import json

old_dataset_path = "evaluation/datasets/rag_eval_dataset.json"
with open(old_dataset_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Keep the first 2 old questions (replace the other 2)
new_data = data[:2]

new_questions = [
  {
    "input": "What was the main challenge in printing certain configurations before using AI, according to Azza Fadhel?",
    "target_article_id": "art_a009616ef1586305"
  },
  {
    "input": "How many printing configurations had already failed in earlier experiments when the researchers started their work?",
    "target_article_id": "art_a009616ef1586305"
  },
  {
    "input": "What are the potential gastrointestinal side effects of taking too much Vitamin C?",
    "target_article_id": "art_41eacdc167cd47be"
  },
  {
    "input": "Why might excessive Vitamin C intake lead to kidney stones?",
    "target_article_id": "art_41eacdc167cd47be"
  },
  {
    "input": "Which foundation provided early funding for the project in 2016?",
    "target_article_id": "art_a511c815af64bf16"
  },
  {
    "input": "Who is Lucia Crivelli and what is her role in the lifestyle intervention study?",
    "target_article_id": "art_50093d064b156524"
  },
  {
    "input": "How did the researchers modify the U.S. POINTER model for Latin American populations?",
    "target_article_id": "art_50093d064b156524"
  },
  {
    "input": "How many study sites across Latin America were included in the lifestyle intervention analysis?",
    "target_article_id": "art_50093d064b156524"
  },
  {
    "input": "What specific activities and support did the Systematic Lifestyle Intervention (SLI) group receive?",
    "target_article_id": "art_50093d064b156524"
  }
]

new_data.extend(new_questions)

with open(old_dataset_path, "w", encoding="utf-8") as f:
    json.dump(new_data, f, indent=2)

print(f"Updated {old_dataset_path} with {len(new_data)} total questions.")

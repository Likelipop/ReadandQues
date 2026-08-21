import { HomepageData } from "../../types";
import { SAMPLE_ARTICLES_DATA } from "./sampleArticles";

export const FALLBACK_HOMEPAGE: HomepageData = {
  status: 'success',
  hero_articles: SAMPLE_ARTICLES_DATA,
  trending_topics: SAMPLE_ARTICLES_DATA.map((a) => ({ id: a.id || a.article_id, title: a.title })),
  daily_vocab: {
    word: 'Resilience',
    phonetic: '/rɪˈzɪl.jəns/',
    part_of_speech: 'noun',
    definition: 'The capacity to withstand or recover quickly from difficult conditions; elasticity.',
    example: 'The educational institution demonstrated extraordinary academic resilience in adopting AI technologies.',
  },
  paraphrase_demo: {
    original: 'Climate change poses severe threats to global food security.',
    paraphrased: 'Global agricultural output and food distribution networks are gravely endangered by anthropogenic climatic instability.',
  },
  recommended_articles: SAMPLE_ARTICLES_DATA,
  articles: SAMPLE_ARTICLES_DATA,
  total_count: SAMPLE_ARTICLES_DATA.length,
  themes: ['All', 'Technology', 'Environment', 'Science', 'Society', 'Economy'],
  genres: ['All', 'academic', 'scientific', 'opinion'],
  nav_themes: [
    { id: 'TECHNOLOGY', name: 'Technology' },
    { id: 'ENVIRONMENT', name: 'Environment' },
    { id: 'SCIENCE', name: 'Science' },
    { id: 'SOCIETY', name: 'Society' },
    { id: 'ECONOMY', name: 'Economy' },
  ],
};

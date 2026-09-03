import { DailyVocab } from '../types';

export const DAILY_VOCAB_POOL: DailyVocab[] = [
  {
    word: 'Resilience',
    phonetic: '/rɪˈzɪliəns/',
    part_of_speech: 'noun',
    band_score: 'IELTS Band 8.5',
    definition: 'The capacity to withstand or recover quickly from difficult conditions.',
    example: 'The country showed remarkable resilience following the economic downturn.',
  },
  {
    word: 'Ubiquitous',
    phonetic: '/juːˈbɪkwɪtəs/',
    part_of_speech: 'adjective',
    band_score: 'IELTS Band 8.5',
    definition: 'Present, appearing, or found everywhere.',
    example: 'Smartphones and mobile broadband have become ubiquitous in contemporary academic environments.',
  },
  {
    word: 'Mitigate',
    phonetic: '/ˈmɪtɪɡeɪt/',
    part_of_speech: 'verb',
    band_score: 'IELTS Band 8.0',
    definition: 'To make something less severe, serious, or painful.',
    example: 'Effective carbon sequestration technologies are essential to mitigate catastrophic climate impacts.',
  },
  {
    word: 'Pedagogical',
    phonetic: '/ˌped.əˈɡɒdʒ.ɪ.kəl/',
    part_of_speech: 'adjective',
    band_score: 'IELTS Band 9.0',
    definition: 'Relating to the theory and practice of education and teaching methods.',
    example: 'The institution adopted progressive pedagogical frameworks integrating real-time cognitive AI agents.',
  },
  {
    word: 'Neuroplasticity',
    phonetic: '/ˌnjʊərəʊplæˈstɪsɪti/',
    part_of_speech: 'noun',
    band_score: 'IELTS Band 9.0',
    definition: 'The ability of the brain to reorganize itself by forming new neural connections throughout life.',
    example: 'Intensive language immersion stimulates adult neuroplasticity and synaptic reorganization.',
  },
  {
    word: 'Ephemeral',
    phonetic: '/ɪˈfemərəl/',
    part_of_speech: 'adjective',
    band_score: 'IELTS Band 8.5',
    definition: 'Lasting for a very short period of time; transitory.',
    example: 'Digital trends are ephemeral, whereas foundational scientific paradigms endure for generations.',
  },
  {
    word: 'Supercritical',
    phonetic: '/ˌsuːpəˈkrɪtɪkəl/',
    part_of_speech: 'adjective',
    band_score: 'IELTS Band 9.0',
    definition: 'Relating to a substance at a temperature and pressure above its thermodynamic critical point.',
    example: 'Novel supercritical thermodynamic extraction systems harness deep-sea geothermal energy along tectonic rifts.',
  },
  {
    word: 'Paradigm',
    phonetic: '/ˈpærədaɪm/',
    part_of_speech: 'noun',
    band_score: 'IELTS Band 8.5',
    definition: 'A typical example, pattern, or overarching conceptual model.',
    example: 'The shift toward distributed renewable energy represents a fundamental paradigm change in global power grids.',
  },
  {
    word: 'Disseminate',
    phonetic: '/dɪˈsemɪneɪt/',
    part_of_speech: 'verb',
    band_score: 'IELTS Band 8.0',
    definition: 'To spread or disperse information, knowledge, or research findings widely.',
    example: 'Open-access digital repositories enable researchers to disseminate peer-reviewed findings instantly.',
  },
  {
    word: 'Pragmatic',
    phonetic: '/præɡˈmætɪk/',
    part_of_speech: 'adjective',
    band_score: 'IELTS Band 8.0',
    definition: 'Dealing with things sensibly and realistically based on practical considerations.',
    example: 'Policymakers formulated a pragmatic roadmap to balance economic expansion with ecological preservation.',
  },
  {
    word: 'Empirical',
    phonetic: '/ɪmˈpɪrɪkəl/',
    part_of_speech: 'adjective',
    band_score: 'IELTS Band 8.5',
    definition: 'Based on, concerned with, or verifiable by observation or experience rather than theory.',
    example: 'Recent empirical investigations demonstrate measurable metacognitive gains through adaptive scaffolding.',
  },
  {
    word: 'Concomitant',
    phonetic: '/kənˈkɒmɪtənt/',
    part_of_speech: 'adjective',
    band_score: 'IELTS Band 9.0',
    definition: 'Naturally accompanying or associated with an event or phenomenon.',
    example: 'Rapid industrial automation brings concomitant shifts in workforce development and educational requirements.',
  },
  {
    word: 'Juxtaposition',
    phonetic: '/ˌdʒʌkstəpəˈzɪʃən/',
    part_of_speech: 'noun',
    band_score: 'IELTS Band 8.5',
    definition: 'The placement of two things close together with contrasting effect.',
    example: 'The author explores the juxtaposition of ancient philosophical ethics and autonomous algorithmic decision-making.',
  },
  {
    word: 'Salient',
    phonetic: '/ˈseɪliənt/',
    part_of_speech: 'adjective',
    band_score: 'IELTS Band 8.0',
    definition: 'Most noticeable, prominent, or crucial.',
    example: 'The report highlights the most salient variables contributing to sustainable economic stability.',
  },
  {
    word: 'Pernicious',
    phonetic: '/pəˈnɪʃəs/',
    part_of_speech: 'adjective',
    band_score: 'IELTS Band 8.5',
    definition: 'Having a harmful effect, especially in a gradual or subtle way.',
    example: 'Unchecked algorithmic bias poses a pernicious threat to equitable digital services.',
  },
  {
    word: 'Cognitive',
    phonetic: '/ˈkɒɡnɪtɪv/',
    part_of_speech: 'adjective',
    band_score: 'IELTS Band 8.0',
    definition: 'Relating to the mental processes of perception, memory, judgment, and reasoning.',
    example: 'Cognitive AI assistants provide real-time scaffolding tailored to individual learning trajectories.',
  },
];

/**
 * Returns a deterministic Word of the Day based on the calendar date.
 * Matches backend selectors.get_daily_vocab index computation.
 */
export function getDeterministicDailyVocab(date: Date = new Date()): DailyVocab {
  const year = date.getFullYear();
  const month = date.getMonth();
  const day = date.getDate();
  // Python date(1970, 1, 1).toordinal() is 719163
  const daysSinceEpoch = Math.floor(Date.UTC(year, month, day) / 86400000);
  const ordinal = 719163 + daysSinceEpoch;
  const index = Math.abs(ordinal) % DAILY_VOCAB_POOL.length;
  return DAILY_VOCAB_POOL[index];
}

/**
 * Formats a Date object to a readable date banner string e.g. "August 19, 2026".
 */
export function formatVocabDateBanner(date: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(date);
}

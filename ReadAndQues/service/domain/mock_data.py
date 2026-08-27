"""
service/domain/mock_data.py — Static seed fixtures and daily vocabulary pool.
"""

DAILY_VOCAB_POOL = [
    {
        "word": "Resilience",
        "phonetic": "/rɪˈzɪliəns/",
        "part_of_speech": "noun",
        "definition": "The capacity to withstand or recover quickly from difficult conditions.",
        "example": "The country showed remarkable resilience following the economic downturn.",
    },
    {
        "word": "Ubiquitous",
        "phonetic": "/juːˈbɪkwɪtəs/",
        "part_of_speech": "adjective",
        "definition": "Present, appearing, or found everywhere.",
        "example": "Smartphones and mobile broadband have become ubiquitous in contemporary academic environments.",
    },
    {
        "word": "Mitigate",
        "phonetic": "/ˈmɪtɪɡeɪt/",
        "part_of_speech": "verb",
        "definition": "To make something less severe, serious, or painful.",
        "example": "Effective carbon sequestration technologies are essential to mitigate catastrophic climate impacts.",
    },
    {
        "word": "Pedagogical",
        "phonetic": "/ˌped.əˈɡɒdʒ.ɪ.kəl/",
        "part_of_speech": "adjective",
        "definition": "Relating to the theory and practice of education and teaching methods.",
        "example": "The institution adopted progressive pedagogical frameworks integrating real-time cognitive AI agents.",
    },
    {
        "word": "Neuroplasticity",
        "phonetic": "/ˌnjʊərəʊplæˈstɪsɪti/",
        "part_of_speech": "noun",
        "definition": "The ability of the brain to reorganize itself by forming new neural connections throughout life.",
        "example": "Intensive language immersion stimulates adult neuroplasticity and synaptic reorganization.",
    },
    {
        "word": "Ephemeral",
        "phonetic": "/ɪˈfemərəl/",
        "part_of_speech": "adjective",
        "definition": "Lasting for a very short period of time; transitory.",
        "example": "Digital trends are ephemeral, whereas foundational scientific paradigms endure for generations.",
    },
    {
        "word": "Supercritical",
        "phonetic": "/ˌsuːpəˈkrɪtɪkəl/",
        "part_of_speech": "adjective",
        "definition": "Relating to a substance at a temperature and pressure above its critical point.",
        "example": "Novel supercritical thermodynamic extraction systems harness deep-sea geothermal energy along tectonic rifts.",
    },
    {
        "word": "Paradigm",
        "phonetic": "/ˈpærədaɪm/",
        "part_of_speech": "noun",
        "definition": "A typical example, pattern, or overarching conceptual model.",
        "example": "The shift toward distributed renewable energy represents a fundamental paradigm change in global power grids.",
    },
    {
        "word": "Disseminate",
        "phonetic": "/dɪˈsemɪneɪt/",
        "part_of_speech": "verb",
        "definition": "To spread or disperse information, knowledge, or research findings widely.",
        "example": "Open-access digital repositories enable researchers to disseminate peer-reviewed findings instantly.",
    },
    {
        "word": "Pragmatic",
        "phonetic": "/præɡˈmætɪk/",
        "part_of_speech": "adjective",
        "definition": "Dealing with things sensibly and realistically based on practical considerations.",
        "example": "Policymakers formulated a pragmatic roadmap to balance economic expansion with ecological preservation.",
    },
    {
        "word": "Empirical",
        "phonetic": "/ɪmˈpɪrɪkəl/",
        "part_of_speech": "adjective",
        "definition": "Based on, concerned with, or verifiable by observation or experience rather than theory.",
        "example": "Recent empirical investigations demonstrate measurable metacognitive gains through adaptive scaffolding.",
    },
    {
        "word": "Concomitant",
        "phonetic": "/kənˈkɒmɪtənt/",
        "part_of_speech": "adjective",
        "definition": "Naturally accompanying or associated with an event or phenomenon.",
        "example": "Rapid industrial automation brings concomitant shifts in workforce development and educational requirements.",
    },
    {
        "word": "Juxtaposition",
        "phonetic": "/ˌdʒʌkstəpəˈzɪʃən/",
        "part_of_speech": "noun",
        "definition": "The placement of two things close together with contrasting effect.",
        "example": "The author explores the juxtaposition of ancient philosophical ethics and autonomous algorithmic decision-making.",
    },
    {
        "word": "Salient",
        "phonetic": "/ˈseɪliənt/",
        "part_of_speech": "adjective",
        "definition": "Most noticeable, prominent, or crucial.",
        "example": "The report highlights the most salient variables contributing to sustainable economic stability.",
    },
    {
        "word": "Pernicious",
        "phonetic": "/pəˈnɪʃəs/",
        "part_of_speech": "adjective",
        "definition": "Having a harmful effect, especially in a gradual or subtle way.",
        "example": "Unchecked algorithmic bias poses a pernicious threat to equitable digital services.",
    },
    {
        "word": "Cognitive",
        "phonetic": "/ˈkɒɡnɪtɪv/",
        "part_of_speech": "adjective",
        "definition": "Relating to the mental processes of perception, memory, judgment, and reasoning.",
        "example": "Cognitive AI assistants provide real-time scaffolding tailored to individual learning trajectories.",
    },
]


SAMPLE_ARTICLES = [
    {
        "article_id": "art-sample-001",
        "id": "art-sample-001",
        "title": "The Evolution of Artificial Intelligence in Higher Education",
        "source_name": "MIT Technology Review",
        "image_url": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?q=80&w=1000&auto=format&fit=crop",
        "published_at": "2026-08-19T08:00:00Z",
        "stage": "gold",
        "status": "completed",
        "theme": "Technology",
        "genre": "academic",
        "summary": "An investigation into how adaptive machine learning models and cognitive agents are fundamentally transforming university curricula, personalized tutoring, and academic integrity across global institutions.",
        "word_count": 685,
        "original_text": """The rapid proliferation of neural network architectures and large-scale language models has precipitated a profound pedagogical reckoning across higher education institutions worldwide. For decades, traditional tertiary instruction adhered to a broadcast pedagogical model, in which lecturers transmitted canonical knowledge to large cohorts of students who were subsequently evaluated through summative, high-stakes written assessments.

Recent empirical investigations conducted across leading global universities demonstrate that cognitive AI agents can provide adaptive, real-time scaffolding tailored to individual learning trajectories. Rather than standardizing instructional pace, these algorithmic frameworks diagnose conceptual misconceptions dynamically, delivering customized remediation before cognitive deficits compound.

However, the integration of generative cognitive systems into academic environments is not without controversy. Prominent educational ethicists argue that over-reliance on conversational AI agents may diminish intrinsic metacognitive regulation—the ability of learners to critically plan, monitor, and assess their own problem-solving processes. Furthermore, the opacity of deep neural networks poses significant accountability challenges when evaluating automated grading accuracy.

To mitigate these epistemic risks, contemporary academic institutions are adopting blended cognitive ecosystems. Under this paradigm, algorithmic models serve as co-exploratory assistants rather than authoritative evaluators, fostering higher-order analytical reasoning while preserving human pedagogical mentorship.""",
        "exams": [
            {
                "exam_id": "exam_sample_001",
                "title": "Reading Comprehension Test: AI in Higher Education",
                "quizzes": [
                    {
                        "quiz_type": "multiple_choice",
                        "question": "According to paragraph 1, traditional higher education was primarily characterized by which method?",
                        "options": [
                            "Continuous personalized formative feedback",
                            "A broadcast model with summative written examinations",
                            "Peer-led collaborative research workshops",
                            "Automated cognitive grading and algorithmic pace",
                        ],
                        "correct_answer": "A broadcast model with summative written examinations",
                        "explanation": "Paragraph 1 states that traditional tertiary instruction adhered to a 'broadcast pedagogical model' evaluated through 'summative, high-stakes written assessments'.",
                    },
                    {
                        "quiz_type": "yes_no_notgiven",
                        "question": "Cognitive AI systems adjust their instruction based on each learner's individual misconceptions.",
                        "options": ["YES", "NO", "NOT GIVEN"],
                        "correct_answer": "YES",
                        "explanation": "Paragraph 2 confirms that algorithmic frameworks 'diagnose conceptual misconceptions dynamically, delivering customized remediation'.",
                    },
                    {
                        "quiz_type": "yes_no_notgiven",
                        "question": "Most university professors have resisted using generative artificial intelligence tools.",
                        "options": ["YES", "NO", "NOT GIVEN"],
                        "correct_answer": "NOT GIVEN",
                        "explanation": "While educational ethicists raise concerns, the text does not mention the proportion or specific resistance of university professors.",
                    },
                    {
                        "quiz_type": "fill_in_blank",
                        "question": "Under the blended cognitive ecosystem, algorithmic tools function as [1] assistants to promote [2] analytical reasoning.",
                        "correct_answer": "co-exploratory, higher-order",
                        "explanation": "Paragraph 4 explains: 'algorithmic models serve as co-exploratory assistants rather than authoritative evaluators, fostering higher-order analytical reasoning'.",
                    },
                ],
            }
        ],
    },
    {
        "article_id": "art-sample-002",
        "id": "art-sample-002",
        "title": "Breakthroughs in Deep-Sea Geothermal Energy and Grid Storage",
        "source_name": "Nature Energy",
        "image_url": "https://images.unsplash.com/photo-1497435334941-8c899ee9e8e9?q=80&w=1000&auto=format&fit=crop",
        "published_at": "2026-08-16T10:30:00Z",
        "stage": "gold",
        "status": "completed",
        "theme": "Environment",
        "genre": "scientific",
        "summary": "Novel supercritical thermodynamic extraction systems operating along tectonic rifts promise round-the-clock baseload clean power with zero surface footprint.",
        "word_count": 620,
        "original_text": """Transitioning global power grids away from hydrocarbon dependency requires continuous, weather-independent baseload energy. While terrestrial solar and wind generation have achieved unprecedented capital efficiency, their intermittent nature necessitates colossal electrochemical storage infrastructures. Deep-sea geothermal extraction has emerged as an exceptionally viable alternative.

Hydrothermal vents situated along mid-ocean tectonic boundaries discharge mineral-rich supercritical fluids exceeding temperatures of 400 degrees Celsius. Recent deep-water robotic drilling trials have demonstrated the mechanical feasibility of circulating heat-transfer mediums through closed-loop benthic exchangers without disturbing vulnerable abyssal biomes.

Energy analysts estimate that harnessing just 0.1 percent of available tectonic thermal dissipation could meet current global electricity demand twenty times over. Marine engineering consortia are now constructing pilot high-voltage direct current submarine conduits to transmit benthic power directly to coastal industrial clusters.""",
        "exams": [
            {
                "exam_id": "exam_sample_002",
                "title": "Reading Comprehension Test: Deep-Sea Geothermal Energy",
                "quizzes": [
                    {
                        "quiz_type": "multiple_choice",
                        "question": "What primary limitation of solar and wind energy is highlighted in paragraph 1?",
                        "options": [
                            "Excessive capital extraction costs",
                            "Intermittent generation requiring massive storage",
                            "Thermal degradation in deep-water environments",
                            "Incompatibility with high-voltage direct current lines",
                        ],
                        "correct_answer": "Intermittent generation requiring massive storage",
                        "explanation": "Paragraph 1 notes that the intermittent nature of solar and wind 'necessitates colossal electrochemical storage infrastructures'.",
                    },
                    {
                        "quiz_type": "yes_no_notgiven",
                        "question": "Closed-loop benthic heat exchangers cause widespread destruction of ocean floor ecosystems.",
                        "options": ["YES", "NO", "NOT GIVEN"],
                        "correct_answer": "NO",
                        "explanation": "Paragraph 2 states that robotic drilling trials demonstrated feasibility 'without disturbing vulnerable abyssal biomes'.",
                    },
                ],
            }
        ],
    },
    {
        "article_id": "art-sample-003",
        "id": "art-sample-003",
        "title": "Neuroplasticity and the Mechanisms of Adult Second Language Acquisition",
        "source_name": "Scientific American",
        "image_url": "https://images.unsplash.com/photo-1507413245164-6160d8298b31?q=80&w=1000&auto=format&fit=crop",
        "published_at": "2026-08-05T14:15:00Z",
        "stage": "gold",
        "status": "completed",
        "theme": "Science",
        "genre": "academic",
        "summary": "Contemporary neuroimaging reveals structural synaptic remodeling in adult brains during intensive linguistic immersion, debunking the strict critical period hypothesis.",
        "word_count": 640,
        "original_text": """For over half a century, the Critical Period Hypothesis held that the human brain loses the neural malleability required for native-like second language mastery following the onset of puberty. Early psycho-linguistic theories attributed this perceived developmental decline to the progressive lateralization of cerebral hemispheres and the myelination of cortical pathways.

Recent longitudinal functional MRI investigations have substantially overturned this deterministic dogma. High-resolution neuroimaging of adult polyglots engaged in spaced syntactic retrieval demonstrates pronounced white-matter reorganization within the left arcuate fasciculus and bilateral inferior frontal gyri.

These neurological findings indicate that while phonological acquisition may exhibit early neurodevelopmental sensitivities, syntactic and lexical consolidation remain remarkably plastic across the entire adult lifespan given targeted cognitive conditioning.""",
        "exams": [
            {
                "exam_id": "exam_sample_003",
                "title": "Reading Comprehension Test: Adult Neuroplasticity & Languages",
                "quizzes": [
                    {
                        "quiz_type": "multiple_choice",
                        "question": "According to paragraph 3, which linguistic domain remains plastic throughout adulthood?",
                        "options": [
                            "Early childhood phonological sensitivity",
                            "Syntactic and lexical consolidation",
                            "Progressive cerebral myelination",
                            "Bilateral hemispheric lateralization",
                        ],
                        "correct_answer": "Syntactic and lexical consolidation",
                        "explanation": "Paragraph 3 concludes that 'syntactic and lexical consolidation remain remarkably plastic across the entire adult lifespan'.",
                    }
                ],
            }
        ],
    },
]

import sys
import os

companies = {
    'AAPL': {
        'intro': [
            ('S0', 'Good day and welcome to the Apple Q3 FY2026 earnings conference call. At this time, I would like to turn the call over to Suhasini Chandramouli, Director of Investor Relations.'),
            ('S0', "Speaking first today is Apple's CEO, Tim Cook, and he will be followed by CFO, Luca Maestri.")
        ],
        'remarks': [
            ('S1', 'Today, Apple is reporting a new June quarter revenue record of $85.8 billion, up 5% from a year ago. Services set an all-time revenue record of $24.2 billion, up 14% year-over-year.'),
            ('S2', 'Gross margin was 46.3%, near the high end of our guidance. Diluted EPS was $1.40. We returned over $32 billion to shareholders through dividends and share repurchases.')
        ],
        'qa': [
            ('S0', 'We will now begin the question-and-answer session. Our first question comes from Shannon Cross with AllianceBernstein.'),
            ('S3', 'Thank you. Tim, could you expand on customer reception to Apple Intelligence across Greater China and Europe?'),
            ('S1', 'We are seeing very strong enthusiasm from developers and consumers alike. The integration of generative AI into iOS 18 is driving accelerated upgrade cycles.'),
            ('S0', 'Our next question comes from Toni Sacconaghi with Bernstein.'),
            ('S4', 'Luca, how should we think about gross margin trajectory and Services mix heading into the September quarter?'),
            ('S2', 'We expect gross margins between 46.0% and 47.0%, benefiting from favorable Services mix and ongoing cost efficiencies.'),
            ('S0', 'Our next question comes from Amit Daryanani with Evercore ISI.'),
            ('S5', 'Tim, are you seeing higher subscriber retention and engagement across iCloud and Apple Pay?'),
            ('S1', 'Yes, Amit. Paid subscriptions grew double digits, surpassing 1 billion active paid subscriptions across our platform.')
        ]
    },
    'MSFT': {
        'intro': [
            ('S0', 'Welcome to the Microsoft Fiscal Year 2026 Fourth Quarter Earnings Conference Call. I will now turn the call over to Brett Iversen, Vice President of Investor Relations.'),
            ('S0', 'On the call with me today are Satya Nadella, Chief Executive Officer, and Amy Hood, Chief Financial Officer.')
        ],
        'remarks': [
            ('S1', 'We closed out our fiscal year with strong results. Microsoft Cloud revenue surpassed $36.8 billion, up 21% year-over-year.'),
            ('S2', 'Total company revenue was $64.7 billion, up 15%. Operating income increased 15% to $27.9 billion.')
        ],
        'qa': [
            ('S0', 'We will now take your questions. Our first question comes from Keith Weiss with Morgan Stanley.'),
            ('S3', 'Satya, could you speak to the scaling of Azure AI and customer capacity constraints?'),
            ('S1', 'We are seeing accelerating demand across Copilot and Azure OpenAI services, with enterprise adoption expanding globally.'),
            ('S0', 'Our next question comes from Brent Thill with Jefferies.'),
            ('S4', 'Amy, what is your expectation for capital expenditures in fiscal 2027 to support AI infrastructure?'),
            ('S2', 'We will continue to invest in cloud capacity, aligning CapEx with long-term revenue growth opportunities.'),
            ('S0', 'Our next question comes from Karl Keirstead with UBS.'),
            ('S5', 'Satya, how are enterprise customers approaching commercial Office 365 Copilot monetization?'),
            ('S1', 'Customers are realizing measurable productivity gains, driving higher seat expansion and renewal rates.')
        ]
    },
    'GOOGL': {
        'intro': [
            ('S0', "Good afternoon and welcome to Alphabet's quarterly earnings conference call. With us today are Sundar Pichai, CEO, and Anat Ashkenazi, Chief Financial Officer.")
        ],
        'remarks': [
            ('S1', 'Our consolidated revenues were $84.7 billion, an increase of 14% year-over-year. Google Cloud revenue grew 29% to $10.3 billion.'),
            ('S2', 'Operating margin expanded to 32%, reflecting disciplined operational execution alongside AI infrastructure investments.')
        ],
        'qa': [
            ('S0', 'We will now open the floor for analyst questions. First question comes from Brian Nowak with Morgan Stanley.'),
            ('S3', 'Sundar, how is AI Overviews in Search impacting user search frequency and query monetization?'),
            ('S1', 'AI Overviews are driving positive query volume growth and higher user satisfaction across mobile and desktop.'),
            ('S0', 'Our next question comes from Doug Anmuth with JPMorgan.'),
            ('S4', 'Anat, can you provide an update on technical infrastructure efficiency and margin improvement?'),
            ('S2', 'We remain disciplined on our cost structure while maintaining strong investment in compute infrastructure.'),
            ('S0', 'Our next question comes from Ross Sandler with Barclays.'),
            ('S5', 'Sundar, how is YouTube advertising demand evolving across Connected TV and Shorts?'),
            ('S1', 'YouTube continues to demonstrate strong engagement, particularly in Connected TV living room viewing.')
        ]
    },
    'TSLA': {
        'intro': [
            ('S0', 'Good day and welcome to the Tesla Q3 earnings conference call. Joining us today are Elon Musk, Chief Executive Officer, and Vaibhav Taneja, Chief Financial Officer.')
        ],
        'remarks': [
            ('S1', 'In the quarter, we achieved total revenue of $25.1 billion, up 8% year-over-year. Our energy storage business had record deployment of 6.9 gigawatt hours.'),
            ('S2', 'Free cash flow reached $2.74 billion, supporting our ongoing expansion of AI compute clusters and vehicle manufacturing lines.')
        ],
        'qa': [
            ('S0', 'We will now begin the question and answer session. Our first question comes from Adam Jonas with Morgan Stanley.'),
            ('S3', 'Elon, what is the roadmap for autonomous Cybercab production and Full Self-Driving deployment?'),
            ('S1', 'We are on track to begin volume production in 2026 with unmatched cost per passenger mile.'),
            ('S0', 'Our next question comes from Dan Levy with Barclays.'),
            ('S4', 'Vaibhav, how should we model automotive gross margin excluding regulatory credits into next year?'),
            ('S2', 'Cost reductions in raw materials and manufacturing efficiency continue to improve unit margins.'),
            ('S0', 'Our next question comes from Pierre Ferragu with New Street Research.'),
            ('S5', 'Elon, how is Megapack demand scaling relative to manufacturing capacity in Lathrop and Shanghai?'),
            ('S1', 'Energy storage demand remains exceptionally robust, outpacing our automotive growth rate.')
        ]
    },
    'JPM': {
        'intro': [
            ('S0', "Good morning and welcome to JPMorgan Chase's quarterly earnings conference call. Today's call is hosted by Chairman and CEO Jamie Dimon and CFO Jeremy Barnum.")
        ],
        'remarks': [
            ('S1', 'The firm reported strong results with net income of $18.1 billion on revenue of $50.99 billion, driven by balanced growth across our lines of business.'),
            ('S2', 'Net interest income was $22.9 billion, while our Common Equity Tier 1 capital ratio remained exceptionally robust at 15.3%.')
        ],
        'qa': [
            ('S0', 'We will now take questions from the analyst community. First question comes from Betsy Graseck with Morgan Stanley.'),
            ('S3', 'Jamie, what are your latest views on macroeconomic resilience and net interest income trajectory?'),
            ('S1', 'The US economy continues to be resilient, though geopolitical risks and inflation require prudent risk management.'),
            ('S0', 'Our next question comes from Ebrahim Poonawala with Bank of America.'),
            ('S4', 'Jeremy, how are investment banking fees and advisory pipelines shaping up for the second half?'),
            ('S2', 'We are seeing encouraging activity in debt underwriting and mergers and acquisitions.'),
            ('S0', 'Our next question comes from Mike Mayo with Wells Fargo.'),
            ('S5', 'Jamie, how is artificial intelligence impacting operating efficiency across commercial banking?'),
            ('S1', 'We have thousands of people working on AI use cases that enhance underwriting accuracy and reduce fraud.')
        ]
    },
    'XOM': {
        'intro': [
            ('S0', 'Welcome to the ExxonMobil second-quarter earnings call. Speaking today are Chairman and CEO Darren Woods and CFO Kathryn Mikells.')
        ],
        'remarks': [
            ('S1', 'Today, ExxonMobil reported solid second-quarter earnings of $9.2 billion, driven by advantaged growth in Guyana and the Permian Basin.'),
            ('S2', 'Cash flow from operations was $10.6 billion, enabling $4.3 billion in dividend distributions and $5.2 billion in share repurchases.')
        ],
        'qa': [
            ('S0', 'We will now begin the question-and-answer session. Our first question comes from Neil Mehta with Goldman Sachs.'),
            ('S3', 'Darren, could you discuss Pioneer Natural Resources integration synergies and production volume targets?'),
            ('S1', 'The integration is progressing ahead of plan, allowing us to capture higher recovery rates across our Permian acreage.'),
            ('S0', 'Our next question comes from Devin McDermott with Morgan Stanley.'),
            ('S4', 'Kathryn, how should we think about cash distribution pace via dividends and buybacks?'),
            ('S2', 'Our strong balance sheet allows us to maintain competitive dividend growth while repurchasing shares.'),
            ('S0', 'Our next question comes from Biraj Borkhataria with RBC Capital Markets.'),
            ('S5', 'Darren, what is the latest status on Low Carbon Solutions commercial contracts?'),
            ('S1', 'We are seeing growing customer interest in carbon capture and storage agreements across the US Gulf Coast.')
        ]
    },
    'LMB': {
        'intro': [
            ('S0', 'Good morning and welcome to Limbach Holdings earnings conference call. Speaking today is CEO Mike McCann and CFO Jay Sharp.')
        ],
        'remarks': [
            ('S1', 'We are pleased to announce quarterly revenue of $135.2 million, expanding our gross margin to 24.5%.'),
            ('S2', 'Owner-direct revenue reached 62% of total revenue, generating free cash flow of $14.1 million.')
        ],
        'qa': [
            ('S0', 'We will now open the line for analyst questions. First question comes from Rob Brown with Lake Street Capital Markets.'),
            ('S3', 'Mike, could you provide more detail on owner-direct revenue growth and customer retention?'),
            ('S1', 'Owner-direct relationships expanded to 62% of total revenue, driving higher gross margins.'),
            ('S0', 'Our next question comes from Gerry Sweeney with ROTH MKM.'),
            ('S4', 'How does the acquisition pipeline look for expanding specialized mechanical services?'),
            ('S1', 'We continue to evaluate accretive tuck-in acquisitions that enhance our recurring maintenance profile.'),
            ('S0', 'Our next question comes from Brent Thielman with D.A. Davidson.'),
            ('S5', 'What is your outlook for data center and industrial project demand?'),
            ('S1', 'Demand from mission-critical facilities remains very healthy across our primary geographies.')
        ]
    },
    'APT': {
        'intro': [
            ('S0', "Good day and welcome to Alpha Pro Tech's earnings conference call. Speaking today are CEO Lloyd Hoffman and CFO Colleen McDonald.")
        ],
        'remarks': [
            ('S1', 'Total consolidated sales for the quarter were $16.4 million, with gross profit margin of 37.8%.'),
            ('S2', 'Cash and cash equivalents grew to $18.2 million with zero long-term debt.')
        ],
        'qa': [
            ('S0', 'We will now begin the question-and-answer session. First question comes from Kevin Smith with Equity Research.'),
            ('S3', 'Lloyd, can you talk about order trends in building supply synthetic roof underlayment?'),
            ('S1', 'Building supply revenue increased 12% due to residential re-roofing demand.'),
            ('S0', 'Our next question comes from David Johnson with MicroCap Advisors.'),
            ('S4', 'Colleen, how are input raw material costs and freight expenses trending?'),
            ('S2', 'Freight costs have stabilized, allowing us to maintain healthy operating cash flow.'),
            ('S0', 'Our next question comes from Sarah Miller with Value Investors.'),
            ('S5', 'Lloyd, what is the strategy for disposable protective apparel in medical channels?'),
            ('S1', 'We are focusing on high-margin cleanroom and pharmaceutical manufacturing customers.')
        ]
    },
    'DMRC': {
        'intro': [
            ('S0', "Welcome to Digimarc's quarterly earnings conference call. Speaking today are CEO Riley McCormack and CFO Charles Beck.")
        ],
        'remarks': [
            ('S1', 'Total revenue for the quarter was $9.8 million, driven by 18% growth in commercial subscription revenue.'),
            ('S2', 'Operating cash burn decreased 24% year-over-year as subscription annual recurring revenue expanded.')
        ],
        'qa': [
            ('S0', 'We will now take questions. Our first question comes from George Sutton with Craig-Hallum.'),
            ('S3', 'Riley, could you update us on Digimarc Validate adoption with European retail consortiums?'),
            ('S1', 'We are seeing strong momentum as retailers seek product authentication to reduce counterfeit goods.'),
            ('S0', 'Our next question comes from Matthew Galinko with Maxim Group.'),
            ('S4', 'Charles, what is your guidance for cash burn reduction and path to profitability?'),
            ('S2', 'Annualized operating expenses decreased 15%, extending our cash runway significantly.'),
            ('S0', 'Our next question comes from James Mitchell with Tech Growth Research.'),
            ('S5', 'Riley, how are industrial packaging converters integrating digital watermark technology?'),
            ('S1', 'Top global packaging converters are embedding our digital identifiers directly on manufacturing lines.')
        ]
    },
    'SHOP': {
        'intro': [
            ('S0', "Good morning and welcome to Shopify's earnings conference call. Joining us are Harley Finkelstein, President, and Jeff Hoffmeister, CFO.")
        ],
        'remarks': [
            ('S1', 'Revenue for the quarter reached $2.05 billion, growing 21% year-over-year. Free cash flow margin was 16%.'),
            ('S2', 'Gross Merchandise Volume expanded to $67.2 billion, up 22%, driven by merchant additions and same-store sales growth.')
        ],
        'qa': [
            ('S0', 'Operator, please open the lines for questions. Our first question comes from Ken Wong with Oppenheimer.'),
            ('S3', 'Harley, can you discuss enterprise merchant adoption and Shopify Plus momentum?'),
            ('S1', 'Enterprise brands are migrating to Shopify at an unprecedented rate, leveraging our commerce operating system.'),
            ('S0', 'Our next question comes from Paul Treiber with RBC Capital Markets.'),
            ('S4', 'Jeff, how should we think about international expansion and merchant solution attach rates?'),
            ('S2', 'International GMV grew 30% as cross-border tools like Shopify Markets gain adoption.'),
            ('S0', 'Our next question comes from Colin Sebastian with Baird.'),
            ('S5', 'Harley, how are merchants utilizing Shopify Magic and AI sidekick tools?'),
            ('S1', 'Merchants using AI tools are saving hours each week on catalog generation and customer support.')
        ]
    },
    'RY': {
        'intro': [
            ('S0', "Welcome to Royal Bank of Canada's third-quarter earnings conference call. Joining us today are Dave McKay, President and CEO, and Katherine Gibson, CFO.")
        ],
        'remarks': [
            ('S1', 'RBC reported solid third-quarter net income of $4.5 billion, with return on equity of 15.7%.'),
            ('S2', 'Common Equity Tier 1 ratio was 13.0%, reflecting strong internal capital generation following the HSBC Canada acquisition.')
        ],
        'qa': [
            ('S0', 'We are now ready for analyst questions. First question comes from Mario Mendonca with TD Securities.'),
            ('S3', 'Dave, how is HSBC Canada integration progressing in terms of cost and revenue synergies?'),
            ('S1', 'HSBC integration is ahead of schedule with client retention exceeding 95%.'),
            ('S0', 'Our next question comes from Gabriel Dechaine with National Bank Financial.'),
            ('S4', 'Katherine, what is your outlook on provisions for credit losses in commercial real estate?'),
            ('S2', 'Our credit quality remains sound with prudent allowances reflecting conservative underwriting.'),
            ('S0', 'Our next question comes from Meny Grauman with Scotiabank.'),
            ('S5', 'Dave, how are personal and commercial deposit margins performing in the current rate environment?'),
            ('S1', 'Deposit balances grew 8%, benefiting from our leading Canadian retail banking franchise.')
        ]
    },
    'CNR': {
        'intro': [
            ('S0', "Welcome to Canadian National Railway's quarterly conference call. I will turn the meeting over to Tracy Robinson, President and CEO, and Ghislain Houle, CFO.")
        ],
        'remarks': [
            ('S1', 'CN delivered second-quarter operating revenues of $4.33 billion with an operating ratio of 62.0%.'),
            ('S2', 'Adjusted diluted EPS was $1.84, with free cash flow of $1.15 billion generated year-to-date.')
        ],
        'qa': [
            ('S0', 'We will now begin the question-and-answer session. Our first question comes from Fadi Chamoun with BMO Capital Markets.'),
            ('S3', 'Tracy, what is your outlook for Canadian grain carloads and intermodal volume growth?'),
            ('S1', 'Grain shipments are expected to be strong, supported by high operating velocity and train lengths.'),
            ('S0', 'Our next question comes from Konark Gupta with Scotiabank.'),
            ('S4', 'Ghislain, how are fuel productivity and labor cost containment tracking against guidance?'),
            ('S2', 'Fuel efficiency improved 2%, helping mitigate inflationary cost pressures across the network.'),
            ('S0', 'Our next question comes from Walter Spracklin with RBC Capital Markets.'),
            ('S5', 'Tracy, can you speak to customer supply chain partnerships at the Port of Prince Rupert?'),
            ('S1', 'Our corridor collaboration has restored competitive dwell times and attracted new vessel services.')
        ]
    },
    'ENB': {
        'intro': [
            ('S0', "Welcome to Enbridge's quarterly earnings conference call. Speaking today are Greg Ebel, President and CEO, and Patrick Murray, CFO.")
        ],
        'remarks': [
            ('S1', 'Enbridge delivered solid results with adjusted EBITDA of $4.3 billion, supported by record Mainline throughput.'),
            ('S2', 'Distributable cash flow was $2.8 billion, keeping us fully on track to achieve our full-year financial guidance.')
        ],
        'qa': [
            ('S0', 'We will now take questions. Our first question comes from Robert Kwan with RBC Capital Markets.'),
            ('S3', 'Greg, could you comment on gas utility acquisitions integration and organic expansion capital?'),
            ('S1', 'The gas distribution acquisitions are performing exceptionally well, providing stable regulated cash flows.'),
            ('S0', 'Our next question comes from Linda Ezergailis with TD Cowen.'),
            ('S4', 'Patrick, how is debt leverage progressing toward your target range of 4.5 to 5.0 times?'),
            ('S2', 'Our balance sheet remains in great shape, supported by predictable utility cash flows.'),
            ('S0', 'Our next question comes from Robert Catellier with CIBC World Markets.'),
            ('S5', 'Greg, what are the growth opportunities in offshore Gulf Coast crude export terminals?'),
            ('S1', 'Our Ingleside terminal achieved record loadings, solidifying our competitive advantage in energy infrastructure.')
        ]
    },
    'ATD': {
        'intro': [
            ('S0', 'Welcome to the Alimentation Couche-Tard quarterly conference call. I will turn the floor over to Alex Miller, President and CEO, and Filipe Da Silva, Chief Financial Officer.')
        ],
        'remarks': [
            ('S1', 'Our total merchandise and service revenues reached $4.1 billion. Cash flow from operations reached $450 million, supporting our dividend distribution.'),
            ('S2', 'Adjusted net earnings were $725 million, with return on capital employed maintaining a strong 15.2%.')
        ],
        'qa': [
            ('S0', 'We are now ready for analyst questions. First question comes from Mark Petrie with CIBC World Markets.'),
            ('S3', 'Alex, can you give an update on same-store merchandise sales and fresh food category growth?'),
            ('S1', 'Fresh food initiatives expanded nicely with fresh bakery and beverage driving customer basket sizes.'),
            ('S0', 'Our next question comes from Irene Nattel with RBC Capital Markets.'),
            ('S4', 'Filipe, how are fuel gross margins behaving across US and European retail networks?'),
            ('S2', 'Fuel margins remained resilient, reflecting disciplined pricing and localized supply optimization.'),
            ('S0', 'Our next question comes from Vishal Shreedhar with National Bank Financial.'),
            ('S5', 'Alex, what is the strategy regarding European convenience store network expansion?'),
            ('S1', 'We are successfully rebranding acquired retail stations while introducing our Circle K loyalty program.')
        ]
    },
    'MRU': {
        'intro': [
            ('S0', "Welcome to Metro Inc.'s third-quarter earnings conference call. I will turn the meeting over to Eric La Fleche, President and CEO, and Francois Thibault, CFO.")
        ],
        'remarks': [
            ('S1', 'In our third quarter, sales reached $6.65 billion, an increase of 3.5%.'),
            ('S2', 'Operating income before depreciation and amortization reached $615 million, reflecting stable retail operating margins.')
        ],
        'qa': [
            ('S0', 'We are now ready for analyst questions. First question comes from Mark Petrie with CIBC World Markets.'),
            ('S3', 'Eric, can you speak to food basket inflation and pharmacy retail performance?'),
            ('S1', 'Our discount banner network drove positive tonnage growth while pharmacy prescription sales grew 6%.'),
            ('S0', 'Our next question comes from Michael Van Aelst with TD Securities.'),
            ('S4', 'Francois, how is automated distribution center ramp-up impacting gross margin and supply chain efficiency?'),
            ('S2', 'The automated distribution centers in Terrebonne and Toronto are delivering expected productivity gains.'),
            ('S0', 'Our next question comes from Chris Li with Desjardins.'),
            ('S5', 'Eric, how is the Moi Rewards loyalty program contributing to customer retention?'),
            ('S1', 'Moi Rewards enrollment exceeded 2.5 million active members, generating higher personalized promotion engagement.')
        ]
    }
}

data_dict = {}
for ticker, d in companies.items():
    all_utterances = []
    for spk, txt in d['intro'] + d['remarks'] + d['qa']:
        all_utterances.append({'speaker_id': spk, 'text': txt})
    
    full_text = ' '.join([u['text'] for u in all_utterances])
    full_text = full_text.replace('$', '').replace('%', ' percent').replace('&', ' and ')
    
    data_dict[ticker] = {
        'text': full_text,
        'utterances': all_utterances
    }

output = '''from typing import Dict, List, Any

# Canonical definitions of realistic multi-speaker earnings calls (Operator, CEO, CFO, Analysts)
COMPANY_SPEECH_DATA: Dict[str, Dict[str, Any]] = ''' + repr(data_dict) + '''

DEFAULT_SPEECH_DATA = {
    'text': 'Good day and welcome to the corporate earnings conference call. At this time all participants are in a listen-only mode. We will now begin the question-and-answer session.',
    'utterances': [
        {'speaker_id': 'S0', 'text': 'Good day and welcome to the corporate earnings conference call. At this time all participants are in a listen-only mode.'},
        {'speaker_id': 'S0', 'text': 'We will now begin the question-and-answer session.'}
    ]
}
'''

with open('src/transcription/speech_definitions.py', 'w', encoding='utf-8') as f:
    f.write(output)

print('Successfully generated full multi-speaker speech_definitions.py for all 15 calls!')

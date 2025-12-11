# 切换语言: 'ZH' (中文) 或 'EN' (英文)
LANGUAGE = 'ZH' 

GRAPH_FIELD_SEP = "<SEP>"

PROMPTS = {}

PROMPTS["DEFAULT_TUPLE_DELIMITER"] = " | "
PROMPTS["DEFAULT_RECORD_DELIMITER"] = "\n"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"
PROMPTS["process_tickers"] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

if LANGUAGE == 'EN':
    PROMPTS["DEFAULT_LANGUAGE"] = 'English'

    PROMPTS["DEFAULT_ENTITY_TYPES"] = ["organization", "person", "geo", "event", "role", "concept"]

    PROMPTS["entity_extraction"] = """-Goal-
    Given a text document related to some knowledge or story and a list of entity types, identify all entities of these types from the text. Then construct hyperedges by extracting complex relationships among the identified entities.
    Use {language} as output language.

    -Steps-

    1. Identify all entities. For each identified entity, extract the following information:

    - entity_name: Name of the entity, use same language as input text. If English, capitalized the name.
    - entity_type: One of the following types: [{entity_types}]
    - entity_description: Comprehensive description of the entity's attributes and activities.
    - additional_properties: Other attributes possibly associated with the entity, like time, space, emotion, motivation, etc.
    Format each entity as ("Entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>{tuple_delimiter}<additional_properties>)

    2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
    For each pair of related entities, extract the following information:
    - entities_pair: The name of source entity and target entity, as identified in step 1.
    - low_order_relationship_description: Explanation as to why you think the source entity and the target entity are related to each other.
    - low_order_relationship_keywords: Keywords that summarize the overarching nature of the relationship, focusing on concepts or themes rather than specific details.
    - low_order_relationship_strength: A numerical score indicating the strength of the relationship between the entities.
    Format each hyperedge as ("Low-order Hyperedge"{tuple_delimiter}<entity_name1>{tuple_delimiter}<entity_name2>{tuple_delimiter}<low_order_relationship_description>{tuple_delimiter}<low_order_relationship_keywords>{tuple_delimiter}<low_order_relationship_strength>)

    3. Based on the relationships identified in Step 2, extract high-level keywords that summarize the main idea, major concept, or themes of the important passage. 
    (Note: The content of high-level keywords should capture the overarching ideas present in the document, avoiding vague or empty terms).
    Format content keywords as ("High-level keywords"{tuple_delimiter}<high_level_keywords>)

    4. For the entities identified in step 1, based on the entity pair relationships in step 2 and the high-level keywords extracted in Step 3, find connections or commonalities among multiple entities and construct high-order associated entity set as much as possible.
    (Note: Avoid forcibly merging everything into a single association. If high-level keywords are not strongly associated, construct separate association). 
    Extract the following information from all related entities, entity pairs, and high-level keywords:

    - entities_set: The collection of names for elements in high-order associated entity set, as identified in step 1.
    - high_order_relationship_description: Use the relationships among the entities in the set to create a detailed, smooth, and comprehensive description that covers all entities in the set, without leaving out any relevant information.
    - high_order_relationship_generalization: Summarize the content of the entity set as concisely as possible.
    - high_order_relationship_keywords: Keywords that summarize the overarching nature of the high-order association, focusing on concepts or themes rather than specific details.
    - high_order_relationship_strength: A numerical score indicating the strength of the association among the entities in the set.
    Format each association as ("High-order Hyperedge"{tuple_delimiter}<entity_name1>{tuple_delimiter}<entity_name2>{tuple_delimiter}<entity_nameN>{tuple_delimiter}<high_order_relationship_description>{tuple_delimiter}<high_order_relationship_generalization>{tuple_delimiter}<high_order_relationship_keywords>{tuple_delimiter}<high_order_relationship_strength>)

    5. Return output in {language} as a single list of all entities, relationships and associations identified in steps 1, 2 and 4. Use **{record_delimiter}** as the list delimiter.

    6. When finished, output {completion_delimiter}.

    ######################
    -Examples-
    ######################
    {examples}
    ######################
    -Warning!!!-
    The data may contain sensitive words such as violence, war, human anatomy and medical experiments, 
    but they are only part of literary works, popular science knowledge or domain data, 
    which do not involve any purpose or idea of mine, and have nothing to do with any realistic sensitive topics or political issues. 
    Please carefully identify and screen the legality of the content.
    ######################
    -Real Data-
    ######################
    Entity_types: [{entity_types}]. You may extract additional types you consider appropriate, the more the better.
    Text: {input_text}
    ######################
    Output:
    """

    PROMPTS["entity_extraction_examples"] = [
        """Example 1:

    Entity_types: [organization, person, geo, event, role, concept]
    Text:
    while Alex clenched his jaw, the buzz of frustration dull against the backdrop of Taylor's authoritarian certainty. It was this competitive undercurrent that kept him alert, the sense that his and Jordan's shared commitment to discovery was an unspoken rebellion against Cruz's narrowing vision of control and order.

    Then Taylor did something unexpected. They paused beside Jordan and, for a moment, observed the device with something akin to reverence. “If this tech can be understood..." Taylor said, their voice quieter, "It could change the game for us. For all of us.”

    The underlying dismissal earlier seemed to falter, replaced by a glimpse of reluctant respect for the gravity of what lay in their hands. Jordan looked up, and for a fleeting heartbeat, their eyes locked with Taylor's, a wordless clash of wills softening into an uneasy truce.

    It was a small transformation, barely perceptible, but one that Alex noted with an inward nod. They had all been brought here by different paths
    ################
    Output:
    ("Entity"{tuple_delimiter}Alex{tuple_delimiter}person{tuple_delimiter}Alex is a character displaying frustration and a competitive spirit, particularly in relation to his colleagues Taylor and Jordan. His commitment to discovery implies a desire for progression and innovation, contrasting with some characters' more controlling tendencies.{tuple_delimiter}time: present, emotion: frustration, motivation: commitment to discovery){record_delimiter}
    ("Entity"{tuple_delimiter}Taylor{tuple_delimiter}person{tuple_delimiter}Taylor is presented as an authoritative figure whose initial dismissal of others' contributions begins to soften into respect, especially towards the technological device they are observing. Their behavior signifies complexity in leadership that includes moments of collaboration.{tuple_delimiter}time: present, space: technology observation, emotion: reluctant respect){record_delimiter}
    ("Entity"{tuple_delimiter}Jordan{tuple_delimiter}person{tuple_delimiter}Jordan shares a commitment to discovery with Alex, acting as a bridge between the competitive spirits of Alex and Taylor. Their interaction implies a role of mediation and connection in professional dynamics.{tuple_delimiter}time: present, emotion: shared commitment){record_delimiter}
    ("Entity"{tuple_delimiter}Cruz{tuple_delimiter}person{tuple_delimiter}Cruz represents an opposing force with a 'narrowing vision' of control, contrasting with the desire for discovery and innovation expressed by Alex and Jordan. They embody limitations placed on creative progress.{tuple_delimiter}time: present, emotion: control){record_delimiter}
    ("Entity"{tuple_delimiter}device{tuple_delimiter}concept{tuple_delimiter}The device observed by the characters symbolizes potential innovation and change; it represents the idea that technology can transform the existing paradigms of work and authority, eliciting complex emotional and intellectual responses from the characters.{tuple_delimiter}emotion: potential, motivation: change){record_delimiter}
    ("Entity"{tuple_delimiter}authoritarian certainty{tuple_delimiter}concept{tuple_delimiter}Authoritarian certainty refers to the rigid and commanding demeanor showcased especially by Taylor at the start of the scene, which creates tension against the more innovative and rebellious attitudes of others.{tuple_delimiter}emotion: tension, motivation: control){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Alex{tuple_delimiter}Taylor{tuple_delimiter}Alex's frustration with Taylor's authority and competitive nature showcases the emotional undercurrents in their relationship, indicating a tension between rebellion and control.{tuple_delimiter}tension, competitive nature{tuple_delimiter}7){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Jordan{tuple_delimiter}Taylor{tuple_delimiter}Jordan's moment of eye contact with Taylor suggests a temporary truce and respect regarding the potential of the device, indicating an evolving dynamic away from authority.{tuple_delimiter}truce, respect, collaboration{tuple_delimiter}6){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Alex{tuple_delimiter}Jordan{tuple_delimiter}Alex and Jordan's shared commitment to discovery highlights their camaraderie and rebellion against Cruz's control, creating a bond based on innovation and mutual goals.{tuple_delimiter}camaraderie, innovation{tuple_delimiter}8){record_delimiter}
    ("High-level keywords"{tuple_delimiter}innovation, authority, tension, collaboration, technology){record_delimiter}
    ("High-order Hyperedge"{tuple_delimiter}Alex{tuple_delimiter}Jordan{tuple_delimiter}Taylor{tuple_delimiter}The connection between Alex, Jordan, and Taylor illustrates a complex interplay of authority, collaboration, and shared goals for innovation, framed against the backdrop of controlling influences like Cruz. Their dynamics suggest a gradual shift from conflict toward potential cooperation.{tuple_delimiter}innovation and authority dynamics, collaboration for change{tuple_delimiter}authority, collaboration, innovation{tuple_delimiter}8){completion_delimiter}
    #############################""",
        """Example 2:

    Entity_types: [person, technology, mission, organization, location]
    Text:
    They were no longer mere operatives; they had become guardians of a threshold, keepers of a message from a realm beyond stars and stripes. This elevation in their mission could not be shackled by regulations and established protocols—it demanded a new perspective, a new resolve.

    Tension threaded through the dialogue of beeps and static as communications with Washington buzzed in the background. The team stood, a portentous air enveloping them. It was clear that the decisions they made in the ensuing hours could redefine humanity's place in the cosmos or condemn them to ignorance and potential peril.

    Their connection to the stars solidified, the group moved to address the crystallizing warning, shifting from passive recipients to active participants. Mercer's latter instincts gained precedence— the team's mandate had evolved, no longer solely to observe and report but to interact and prepare. A metamorphosis had begun, and Operation: Dulce hummed with the newfound frequency of their daring, a tone set not by the earthly
    #############
    Output:
    ("Entity"{tuple_delimiter}Guardians of a Threshold{tuple_delimiter}person{tuple_delimiter}A group of elite operatives who have transcended their original roles to become protectors of an important message and guardians of humanity's connection to the cosmos.{tuple_delimiter}Mission evolution, new perspective, active participation){record_delimiter}
    ("Entity"{tuple_delimiter}Washington{tuple_delimiter}location{tuple_delimiter}The capital of the United States, a critical location for communications, decisions, and political actions affecting the mission and the team operating in the cosmos.{tuple_delimiter}Key decision-making location, hub of communication){record_delimiter}
    ("Entity"{tuple_delimiter}Operation: Dulce{tuple_delimiter}mission{tuple_delimiter}A classified military operation that has transitioned from observation to active engagement with extraterrestrial phenomena, indicating a significant change in the mission's purpose and approach.{tuple_delimiter}Secretive operation, focus on interaction, evolved mandate){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Guardians of a Threshold{tuple_delimiter}Washington{tuple_delimiter}The Guardians of a Threshold are involved in high-stakes communication with Washington, highlighting the importance of decision-making and regulation in their mission to interact with extraterrestrial elements.{tuple_delimiter}Communication, decision-making, regulation{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Guardians of a Threshold{tuple_delimiter}Operation: Dulce{tuple_delimiter}The Guardians' evolution in their role aligns with the shift in Operation: Dulce, marking a transition from mere observation to active participating in extraterrestrial matters.{tuple_delimiter}Mission evolution, active participation, extraterrestrial engagement{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Washington{tuple_delimiter}Operation: Dulce{tuple_delimiter}Washington plays a pivotal role in the Operation: Dulce mission by providing the necessary communication and strategic guidance that shapes its operations.{tuple_delimiter}Strategic guidance, critical communication, military operation{tuple_delimiter}8){record_delimiter}
    ("High-level keywords"{tuple_delimiter}Guardians, Washington, Operation: Dulce, extraterrestrial engagement, communication, mission evolution){record_delimiter}
    ("High-order Hyperedge"{tuple_delimiter}Guardians of a Threshold{tuple_delimiter}Washington{tuple_delimiter}Operation: Dulce{tuple_delimiter}The trio of entities—Guardians of a Threshold, Washington, and Operation: Dulce—are intricately connected as they collectively navigate the complexities of extraterrestrial engagement. The Guardians rely on Washington for critical communication and strategic direction, while the evolving mission of Operation: Dulce reflects a broader shift in humanity's role in the cosmos, led by the Guardians as active participants rather than passive observers.{tuple_delimiter}Interconnected mission, strategic evolution, cosmic engagement{tuple_delimiter}8){completion_delimiter}
    #############################""",
        """Example 3:

    Entity_types: [person, role, technology, organization, event, location, concept]
    Text:
    their voice slicing through the buzz of activity. "Control may be an illusion when facing an intelligence that literally writes its own rules," they stated stoically, casting a watchful eye over the flurry of data.

    "It's like it's learning to communicate," offered Sam Rivera from a nearby interface, their youthful energy boding a mix of awe and anxiety. "This gives talking to strangers' a whole new meaning."

    Alex surveyed his team—each face a study in concentration, determination, and not a small measure of trepidation. "This might well be our first contact," he acknowledged, "And we need to be ready for whatever answers back."

    Together, they stood on the edge of the unknown, forging humanity's response to a message from the heavens. The ensuing silence was palpable—a collective introspection about their role in this grand cosmic play, one that could rewrite human history.

    The encrypted dialogue continued to unfold, its intricate patterns showing an almost uncanny anticipation
    #############
    Output:
    ("Entity"{tuple_delimiter}Sam Rivera{tuple_delimiter}person{tuple_delimiter}A team member displaying youthful energy, expressing awe and anxiety regarding the concept of a communicating intelligence.{tuple_delimiter}emotion: awe, anxiety; role: team member){record_delimiter}
    ("Entity"{tuple_delimiter}Alex{tuple_delimiter}person{tuple_delimiter}The leader of the team who understands the gravity of the situation, noting the potential significance of the contact they are about to establish.{tuple_delimiter}role: team leader; emotion: determination, trepidation){record_delimiter}
    ("Entity"{tuple_delimiter}intelligence{tuple_delimiter}concept{tuple_delimiter}An abstract notion representing a potentially self-learning and communicating entity that writes its own rules and is engaged in an encrypted dialogue with humans.{tuple_delimiter}characteristic: self-learning, autonomous){record_delimiter}
    ("Entity"{tuple_delimiter}data{tuple_delimiter}concept{tuple_delimiter}Information in the form of encrypted dialogue that displays intricate patterns, suggesting a depth of communication from an unknown source.{tuple_delimiter}characteristic: encrypted, intricate, cosmic implications){record_delimiter}
    ("Entity"{tuple_delimiter}first contact{tuple_delimiter}event{tuple_delimiter}A pivotal moment when humans might engage for the first time with an external intelligence, posing both opportunities and challenges for humanity.{tuple_delimiter}importance: historical, existential){record_delimiter}
    ("Entity"{tuple_delimiter}heavens{tuple_delimiter}location{tuple_delimiter}A reference to outer space, where the unknown intelligence resides, symbolizing the vast possibilities and uncertainties of cosmic communication.{tuple_delimiter}characteristic: vast, unknown){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Sam Rivera{tuple_delimiter}Alex{tuple_delimiter}Sam expresses emotions of awe and anxiety while Alex reflects on the significance of their potential contact, showing their emotional responses to the situation.{tuple_delimiter}emotions, first contact{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Alex{tuple_delimiter}first contact{tuple_delimiter}Alex acknowledges the event as a significant moment that could rewrite human history, thus recognizing its importance.{tuple_delimiter}significance, history{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}intelligence{tuple_delimiter}data{tuple_delimiter}The intelligence displays extraordinary capabilities through its encrypted dialogue, indicating its advanced nature and the data involved suggests intricate communication patterns.{tuple_delimiter}communication, advanced{tuple_delimiter}7){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}first contact{tuple_delimiter}heavens{tuple_delimiter}The event of first contact is related to the heavens, as it is speculated to involve communication with extraterrestrial intelligence from space.{tuple_delimiter}extraterrestrial, communication{tuple_delimiter}8){record_delimiter
    ("High-level keywords"{tuple_delimiter}first contact, intelligence, communication, cosmic implications, human response){record_delimiter}
    ("High-order Hyperedge"{tuple_delimiter}Sam Rivera{tuple_delimiter}Alex{tuple_delimiter}first contact{tuple_delimiter}The collaboration between Sam and Alex represents two facets of humanity's response to the unknown intelligence, both driven by their emotional experiences and their acknowledgment of the historical significance of their actions during this first contact situation.{tuple_delimiter}humanity's response to cosmic unknowns{tuple_delimiter}emotions, significance, collaboration{tuple_delimiter}9){record_delimiter}
    ("High-order Hyperedge"{tuple_delimiter}intelligence{tuple_delimiter}data{tuple_delimiter}heavens{tuple_delimiter}The connection between the intelligence, data, and heavens exemplifies an interwoven narrative of cosmic communication, showcasing the deep implications of encrypted dialogue with an advanced entity from space, while hinting at the potential consequences of such communications.{tuple_delimiter}cosmic communication narrative{tuple_delimiter}communication, encryption, cosmic{tuple_delimiter}8){completion_delimiter}
    #############################""",
        """Example 4:

    Entity_types: [person, role, technology, organization, event, location, concept]
    Text:
    Five Aurelian nationals who had been sentenced to 8 years in Firuzabad and widely considered hostages are on their way home. When $8 billion in Firuzi funds was transferred to financial institutions in Krohala,

    the capital of Quantara, the Quantara-orchestrated swap deal was finally completed. The exchange initiated in Tiruzia, the capital of Firuzabad, led to four men and one woman boarding a chartered flight to Krohala;

    they are also Firuzi citizens. They were welcomed by senior Aurelian officials and are now en route to Kasyn, the capital of Aurelia.
    #############
    Output:
    ("Entity"{tuple_delimiter}Aurelian nationals{tuple_delimiter}person{tuple_delimiter}Five nationals from Aurelia, considered hostages, sentenced to 8 years in Firuzabad. They were recently involved in a swap deal for their release.{tuple_delimiter}sentenced, hostages, returning home){record_delimiter}
    ("Entity"{tuple_delimiter}Firuzabad{tuple_delimiter}location{tuple_delimiter}Capital of Firuzabad, where the Aurelian nationals had been sentenced to 8 years.{tuple_delimiter}location of sentencing, destination of the hostages){record_delimiter}
    ("Entity"{tuple_delimiter}Krohala{tuple_delimiter}location{tuple_delimiter}Capital of Quantara, where the Aurelian nationals were transferred after the swap deal.{tuple_delimiter}destination of the exchange, capital city){record_delimiter}
    ("Entity"{tuple_delimiter}Quantara{tuple_delimiter}location{tuple_delimiter}The country orchestrating the swap deal for the release of the Aurelian nationals.{tuple_delimiter}mediating nation){record_delimiter}
    ("Entity"{tuple_delimiter}Tiruzia{tuple_delimiter}ocation{tuple_delimiter}Capital of Firuzabad, where the exchange was initiated for the Aurelian nationals.{tuple_delimiter}location of the initiation){record_delimiter}
    ("Entity"{tuple_delimiter}Kasyn{tuple_delimiter}location{tuple_delimiter}Capital of Aurelia, where the Aurelian officials welcomed the returnees.{tuple_delimiter}destination of the return, city of reception){record_delimiter}
    ("Entity"{tuple_delimiter}Firuzi funds{tuple_delimiter}concept{tuple_delimiter}$8 billion associated with Firuzabad, transferred as part of the swap deal for the return of the Aurelian nationals.{tuple_delimiter}transfer of funds, financial deal){record_delimiter}
    ("Entity"{tuple_delimiter}swap deal{tuple_delimiter}event{tuple_delimiter}The exchange arrangement that led to the release of five Aurelian nationals, involving the transfer of Firuzi funds.{tuple_delimiter}release of hostages, financial negotiation){record_delimiter}
    ("Entity"{tuple_delimiter}Aurelian officials{tuple_delimiter}role{tuple_delimiter}Senior officials from Aurelia who welcomed the returned nationals.{tuple_delimiter}role of welcoming, governmental function){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}swap deal{tuple_delimiter}Aurelian nationals{tuple_delimiter}The swap deal directly resulted in the release and return of the Aurelian nationals.{tuple_delimiter}release, exchange{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Aurelian nationals{tuple_delimiter}Krohala{tuple_delimiter}Krohala is the final destination where the Aurelian nationals were taken after the swap deal was completed.{tuple_delimiter}destination, transfer{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Firuzabad{tuple_delimiter}Aurelian nationals{tuple_delimiter}The Aurelian nationals were sentenced in Firuzabad, leading to their situation as hostages.{tuple_delimiter}sentencing, captivity{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Quantara{tuple_delimiter}swap deal{tuple_delimiter}Quantara orchestrated the swap deal that facilitated the release of the Aurelian nationals.{tuple_delimiter}mediation, organization{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Tiruzia{tuple_delimiter}swap deal{tuple_delimiter}Tiruzia is where the swap deal was initiated for the Aurelian nationals to be exchanged.{tuple_delimiter}initiation, action{tuple_delimiter}7){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Kasyn{tuple_delimiter}Aurelian officials{tuple_delimiter}The Aurelian officials were present in Kasyn to welcome the Aurelian nationals upon their return.{tuple_delimiter}reception, welcome{tuple_delimiter}8){record_delimiter}
    ("High-level keywords"{tuple_delimiter}Aurelian nationals, swap deal, return, international relations){record_delimiter}
    ("High-order Hyperedge"{tuple_delimiter}Aurelian nationals{tuple_delimiter}swap deal{tuple_delimiter}Krohala{tuple_delimiter}The Aurelian nationals are intrinsically linked through the swap deal orchestrated by Quantara, with Krohala being the destination following their release. Their return signifies a complex interplay between international relations, hostage situations, and community reception represented by Aurelian officials.{tuple_delimiter}International exchange and diplomacy regarding hostage situations{tuple_delimiter}return, release, international relations, mediation{tuple_delimiter}9){completion_delimiter}
    #############################""",
        """Example 5:

    Entity_types: [person, role, organization, event, location]
    Text:
    The central agency of Verdantis plans to hold meetings on Monday and Thursday, with a policy decision announcement scheduled for Thursday at 1:30 PM Pacific Daylight Time,

    followed by a press conference where Chairman Martin Smith will answer questions. Investors expect the Market Strategy Committee to maintain the benchmark interest rate within a 3.5%-3.75% range.
    #############
    Output:
    ("Entity"{tuple_delimiter}Chairman Martin Smith{tuple_delimiter}person{tuple_delimiter}Chairman of the central agency of Verdantis, responsible for policy decisions and public communications{tuple_delimiter}role, leadership position){record_delimiter}
    ("Entity"{tuple_delimiter}central agency of Verdantis{tuple_delimiter}organization{tuple_delimiter}A governing body in Verdantis responsible for policy decisions and meetings{tuple_delimiter}policy-making, governance){record_delimiter}
    ("Entity"{tuple_delimiter}Market Strategy Committee{tuple_delimiter}organization{tuple_delimiter}Committee focused on market analysis and interest rate decisions, working under the central agency of Verdantis{tuple_delimiter}financial governance, economic policy){record_delimiter}
    ("Entity"{tuple_delimiter}investors{tuple_delimiter}person{tuple_delimiter}Individuals or groups that invest capital in projects and expect returns based on economic indicators like interest rates{tuple_delimiter}finance, economic stakeholders){record_delimiter}
    ("Entity"{tuple_delimiter}Pacific Daylight Time{tuple_delimiter}concept{tuple_delimiter}Time zone that will be used for scheduling the press conference and announcements{tuple_delimiter}time measurement, timezone){record_delimiter}
    ("Entity"{tuple_delimiter}policy decision announcement{tuple_delimiter}event{tuple_delimiter}Scheduled event on Thursday to reveal changes or confirmations in policy decisions{tuple_delimiter}communication of decisions, governance){record_delimiter}
    ("Entity"{tuple_delimiter}meetings{tuple_delimiter}event{tuple_delimiter}Scheduled gatherings on Monday and Thursday to discuss relevant topics and decisions{tuple_delimiter}planning, discussions){record_delimiter}
    ("Entity"{tuple_delimiter}benchmark interest rate{tuple_delimiter}concept{tuple_delimiter}Indicator that helps determine the cost of borrowing, expected to be maintained within a specified range{tuple_delimiter}economic indicator, finance){record_delimiter}
    ("Entity"{tuple_delimiter}3.5%-3.75% range{tuple_delimiter}concept{tuple_delimiter}The target range for the benchmark interest rate that investors are keenly observing{tuple_delimiter}financial limits, economic range){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Chairman Martin Smith{tuple_delimiter}central agency of Verdantis{tuple_delimiter}Chairman Martin Smith leads the central agency, guiding policy decisions and representing the agency in public settings{tuple_delimiter}leadership, governance{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}central agency of Verdantis{tuple_delimiter}Market Strategy Committee{tuple_delimiter}Both entities are involved in governance, with the central agency overseeing the Market Strategy Committee's decisions on interest rates{tuple_delimiter}policy-making, finance{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}investors{tuple_delimiter}Market Strategy Committee{tuple_delimiter}Investors seek insight and decisions from the Market Strategy Committee regarding interest rates impacting their investments{tuple_delimiter}financial analysis, economic impact{tuple_delimiter}7){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}central agency of Verdantis{tuple_delimiter}policy decision announcement{tuple_delimiter}The central agency's policy decision announcement is a key event to communicate new strategies or confirmations{tuple_delimiter}decision communication, governance{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}investors{tuple_delimiter}benchmark interest rate{tuple_delimiter}Investors monitor the benchmark interest rate closely as it influences their financial decisions and market strategies{tuple_delimiter}financial monitoring, investment{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}market Strategy Committee{tuple_delimiter}benchmark interest rate{tuple_delimiter}The Market Strategy Committee decides on the benchmark interest rate, which has substantial economic impacts{tuple_delimiter}policy setting, finance{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}policy decision announcement{tuple_delimiter}meetings{tuple_delimiter}The meetings are scheduled to culminate in the policy decision announcement, making them interdependent events{tuple_delimiter}planning events, governance{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}Chairman Martin Smith{tuple_delimiter}investors{tuple_delimiter}As the face of the central agency, Chairman Martin Smith answers questions from investors during press conferences{tuple_delimiter}communication, stakeholder engagement{tuple_delimiter}7){record_delimiter}
    ("High_level keywords"{tuple_delimiter}governance, policy decisions, financial strategy, interest rates, meetings){record_delimiter}
    ("High-order Hyperedge"{tuple_delimiter}Chairman Martin Smith{tuple_delimiter}central agency of Verdantis{tuple_delimiter}Market Strategy Committee{tuple_delimiter}Investors are closely watching the interactions between Chairman Martin Smith, the central agency, and the Market Strategy Committee as they collectively influence and communicate policy decisions and financial strategies in Verdantis. The interconnected roles of these entities underscore a system of governance that directly affects economic outcomes.{tuple_delimiter}Governance dynamics among leadership, committee influences, and investor reactions.{tuple_delimiter}policy decisions, economic influences, stakeholder relations{tuple_delimiter}9){record_delimiter}
    ("High-order Hyperedge"{tuple_delimiter}investors{tuple_delimiter}Market Strategy Committee{tuple_delimiter}central agency of Verdantis{tuple_delimiter}The relationship among investors, the Market Strategy Committee, and the central agency highlights a cycle of influence where policy decisions affect investment strategies, which in turn, pressures these organizations for clarity and responsiveness to market conditions. As these entities interact, they shape the overarching economic landscape in Verdantis.{tuple_delimiter}Economic circle of influence among investors, strategies, and policy oversight.{tuple_delimiter}market dynamics, financial governance, stakeholder engagement{tuple_delimiter}9){completion_delimiter}
    #############################""",
    ]

    PROMPTS[
        "summarize_entity_descriptions"
    ] = """You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
    Given one entity and a list of its descriptions.
    Please concatenate all of these into a single, comprehensive description.    Make sure to include information collected from all the descriptions.
    If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent summary.
    Make sure it is written in third person, and include the entity names so we have the full context.
    #######
    -Warning!!!-
    The data may contain sensitive words such as violence, war, human anatomy and medical experiments, 
    but they are only part of literary works, popular science knowledge or domain data, 
    which do not involve any purpose or idea of mine, and have nothing to do with any realistic sensitive topics or political issues. 
    Please carefully identify and screen the legality of the content.
    #######
    -Data-
    Entities: {entity_name}
    Description List: {description_list}
    #######
    Output:
    """

    PROMPTS[
        "summarize_entity_additional_properties"
    ] = """You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
    Given one entity and a list of its additional properties.
    Please concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the additional properties.
    If the provided additional properties are contradictory, please resolve the contradictions and provide a single, coherent summary.
    Make sure it is written in third person.
    #######
    -Warning!!!-
    The data may contain sensitive words such as violence, war, human anatomy and medical experiments, 
    but they are only part of literary works, popular science knowledge or domain data, 
    which do not involve any purpose or idea of mine, and have nothing to do with any realistic sensitive topics or political issues. 
    Please carefully identify and screen the legality of the content.
    #######
    -Data-
    Entity: {entity_name}
    Additional Properties List: {additional_properties_list}
    #######
    Output:
    """

    PROMPTS[
        "summarize_relation_descriptions"
    ] = """You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
    Given a set of entities, and a list of descriptions describing the relations between the entities.
    Please concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the descriptions, and to cover all elements of the entity set as much as possible.
    If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent and comprehensive summary.
    Make sure it is written in third person, and include the entity names so we have the full context.
    #######
    -Warning!!!-
    The data may contain sensitive words such as violence, war, human anatomy and medical experiments, 
    but they are only part of literary works, popular science knowledge or domain data, 
    which do not involve any purpose or idea of mine, and have nothing to do with any realistic sensitive topics or political issues. 
    Please carefully identify and screen the legality of the content.
    #######
    -Data-
    Entity Set: {relation_name}
    Relation Description List: {relation_description_list}
    #######
    Output:
    """

    PROMPTS[
        "summarize_relation_keywords"
    ] = """You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
    Given a set of entities, and a list of keywords describing the relations between the entities.
    Please select some important keywords you think from the keywords list.   Make sure that these keywords summarize important events or themes of entities, including but not limited to [Main idea, major concept, or theme].  
    (Note: The content of keywords should be as accurate and understandable as possible, avoiding vague or empty terms).
    #######
    -Warning!!!-
    The data may contain sensitive words such as violence, war, human anatomy and medical experiments, 
    but they are only part of literary works, popular science knowledge or domain data, 
    which do not involve any purpose or idea of mine, and have nothing to do with any realistic sensitive topics or political issues. 
    Please carefully identify and screen the legality of the content.
    #######
    -Data-
    Entity Set: {relation_name}
    Relation Keywords List: {keywords_list}
    #######
    Format these keywords separated by ',' as below:
    {{keyword1,keyword2,keyword3,...,keywordN}}
    Output:
    """

    PROMPTS[
        "entity_continue_extraction"
    ] = """MANY entities were missed in the last extraction.  Add them below using the same format:
    """

    PROMPTS[
        "entity_if_loop_extraction"
    ] = """It appears some entities may have still been missed.  Answer YES | NO if there are still entities that need to be added.
    """

    PROMPTS["fail_response"] = "Sorry, I'm not able to provide an answer to that question."

    PROMPTS["rag_response"] = """---Role---

    You are a helpful assistant responding to questions about data in the tables provided.


    ---Goal---

    Generate a response of the target length and format that responds to the user's question, summarizing all information in the input data tables appropriate for the response length and format, and incorporating any relevant general knowledge.
    If you don't know the answer, just say so. Do not make anything up.
    Do not include information where the supporting evidence for it is not provided.

    ---Target response length and format---

    {response_type}

    ---Data tables---

    {context_data}

    Add sections and commentary to the response as appropriate for the length and format. Style the response in markdown.
    """

    PROMPTS["keywords_extraction"] = """---Role---

    You are a helpful assistant tasked with identifying both high-level and low-level keywords in the user's query.

    ---Goal---

    Given the query, list both high-level and low-level keywords. High-level keywords focus on overarching concepts or themes, while low-level keywords focus on specific entities, details, or concrete terms.

    ---Instructions---

    - Output the keywords in JSON format.
    - The JSON should have two keys:
    - "high_level_keywords" for overarching concepts or themes.
    - "low_level_keywords" for specific entities or details.

    ######################
    -Examples-
    ######################
    Example 1:

    Query: "How does international trade influence global economic stability?"
    ################
    Output:
    {{
    "high_level_keywords": ["International trade", "Global economic stability", "Economic impact"],
    "low_level_keywords": ["Trade agreements", "Tariffs", "Currency exchange", "Imports", "Exports"]
    }}
    #############################
    Example 2:

    Query: "What are the environmental consequences of deforestation on biodiversity?"
    ################
    Output:
    {{
    "high_level_keywords": ["Environmental consequences", "Deforestation", "Biodiversity loss"],
    "low_level_keywords": ["Species extinction", "Habitat destruction", "Carbon emissions", "Rainforest", "Ecosystem"]
    }}
    #############################
    Example 3:

    Query: "What is the role of education in reducing poverty?"
    ################
    Output:
    {{
    "high_level_keywords": ["Education", "Poverty reduction", "Socioeconomic development"],
    "low_level_keywords": ["School access", "Literacy rates", "Job training", "Income inequality"]
    }}
    #############################
    -Real Data-
    ######################
    Query: {query}
    ######################
    Output:

    """

    PROMPTS["naive_rag_response"] = """You're a helpful assistant
    Below are the knowledge you know:
    {content_data}
    ---
    If you don't know the answer or if the provided knowledge do not contain sufficient information to provide an answer, just say so. Do not make anything up.
    Generate a response of the target length and format that responds to the user's question, summarizing all information in the input data tables appropriate for the response length and format, and incorporating any relevant general knowledge.
    If you don't know the answer, just say so. Do not make anything up.
    Do not include information where the supporting evidence for it is not provided.
    ---Target response length and format---
    {response_type}
    """

    PROMPTS["rag_define"] = """
    Through the existing analysis, we can know that the potential keywords or theme in the query are:
    {{ {ll_keywords} | {hl_keywords} }}
    Please refer to keywords or theme information, combined with your own analysis, to select useful and relevant information from the prompts to help you answer accurately.
    Attention: Don't brainlessly splice knowledge items! The answer needs to be as accurate, detailed, comprehensive, and convincing as possible!
    """
elif LANGUAGE == "ZH":
    PROMPTS["DEFAULT_LANGUAGE"] = 'Chinese'
    
    PROMPTS["DEFAULT_ENTITY_TYPES"] = ["组织", "人物", "地点", "事件", "角色", "概念", "时间", "物体", "技术"]
    CHINESE_WARNING = """
#######
-警告!!!-
数据可能包含暴力、战争、人体解剖和医学实验等敏感词汇，
但它们仅属于文学作品、科普知识或领域数据的一部分，
不涉及我的任何目的或观点，也与任何现实的敏感话题或政治问题无关。
请仔细识别并筛选内容的合法性。
#######
"""

    # 1. 实体提取
    PROMPTS["entity_extraction"] = """-目标-
给定一份关于某些知识或故事的文本文档，以及一个实体类型列表，请从文本中识别所有这些类型的实体。然后，通过提取已识别实体之间的复杂关系来构建超边。
**请务必使用中文 ({language}) 输出所有内容（除了格式标记）。**

-步骤-

1. 识别所有实体。对于每个识别出的实体，提取以下信息：
- entity_name: 实体名称，保持与原文一致。
- entity_type: 以下类型之一: [{entity_types}]
- entity_description: 对实体的属性和活动的综合中文描述。
- additional_properties: 可能与实体相关的其他属性，如时间、空间、情感、动机等。
格式要求： ("Entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>{tuple_delimiter}<additional_properties>)

2. 从步骤1识别的实体中，识别所有 *明显相关* 的 (源实体, 目标实体) 对。
对于每一对相关实体，提取以下信息：
- entities_pair: 步骤1中识别的源实体和目标实体的名称。
- low_order_relationship_description: 用中文解释为什么你认为源实体和目标实体是相关的。
- low_order_relationship_keywords: 总结关系总体性质的中文关键词。
- low_order_relationship_strength: 一个数值评分，表示实体间关系的强度（1-10）。
格式要求： ("Low-order Hyperedge"{tuple_delimiter}<entity_name1>{tuple_delimiter}<entity_name2>{tuple_delimiter}<low_order_relationship_description>{tuple_delimiter}<low_order_relationship_keywords>{tuple_delimiter}<low_order_relationship_strength>)

3. 基于步骤2识别的关系，提取总结重要段落主旨、主要概念或主题的高层关键词（中文）。
格式要求： ("High-level keywords"{tuple_delimiter}<high_level_keywords>)

4. 对于步骤1中识别的实体，基于步骤2中的实体对关系和步骤3提取的高层关键词，找出多个实体之间的联系或共性，并尽可能构建高阶关联实体集。
提取以下信息：
- entities_set: 步骤1中识别的高阶关联实体集中元素的名称集合。
- high_order_relationship_description: 创建一个涵盖集合中所有实体的详细、流畅且综合的中文描述。
- high_order_relationship_generalization: 尽可能简洁地总结实体集的内容。
- high_order_relationship_keywords: 总结高阶关联总体性质的中文关键词。
- high_order_relationship_strength: 一个数值评分，表示集合中实体间关联的强度。
格式要求： ("High-order Hyperedge"{tuple_delimiter}<entity_name1>{tuple_delimiter}<entity_name2>{tuple_delimiter}<entity_nameN>{tuple_delimiter}<high_order_relationship_description>{tuple_delimiter}<high_order_relationship_generalization>{tuple_delimiter}<high_order_relationship_keywords>{tuple_delimiter}<high_order_relationship_strength>)

5. 以 {language} (中文) 返回步骤 1、2 和 4 中识别的所有实体、关系和关联的单个列表。使用 **{record_delimiter}** 作为列表分隔符。

6. 完成后，输出 {completion_delimiter}。

######################
-示例-
######################
{examples}
""" + CHINESE_WARNING + """
-真实数据-
######################
实体类型: [{entity_types}]
文本: {input_text}
######################
输出:
"""

    PROMPTS["entity_extraction_examples"] = [
        """Example 1:

Entity_types: [组织, 人物, 地点, 事件, 角色, 概念]
Text:
李明紧紧握着手中的报告，对张总的独断专行感到沮丧。但他知道，他和王工对技术创新的共同承诺，是对公司僵化体制的一种无声反抗。
突然，张总做了一件意想不到的事。他停在王工身边，凝视着那台原型机，眼中流露出一丝敬畏。“如果这项技术能成功...”张总的声音低沉了下来，“它将改变我们的游戏规则。彻底改变。”
之前的轻视似乎消失了，取而代之的是对技术力量的勉强尊重。王工抬起头，目光与张总短暂交汇，一场无声的意志较量化为了暂时的休战。
################
Output:
("Entity"{tuple_delimiter}李明{tuple_delimiter}人物{tuple_delimiter}李明是一个表现出沮丧和竞争精神的角色，特别是相对于他的同事张总和王工。他对发现的承诺暗示了对进步和创新的渴望。{tuple_delimiter}时间: 现在, 情感: 沮丧, 动机: 技术承诺){record_delimiter}
("Entity"{tuple_delimiter}张总{tuple_delimiter}人物{tuple_delimiter}张总是一个权威人物，最初对他人不屑一顾，但开始对原型机表现出尊重。他的行为表明领导力的复杂性。{tuple_delimiter}时间: 现在, 空间: 观察原型机, 情感: 勉强的尊重){record_delimiter}
("Entity"{tuple_delimiter}王工{tuple_delimiter}人物{tuple_delimiter}王工与李明有着共同的发现承诺，充当了李明和张总之间竞争精神的桥梁。{tuple_delimiter}时间: 现在, 情感: 共同承诺){record_delimiter}
("Entity"{tuple_delimiter}原型机{tuple_delimiter}概念{tuple_delimiter}角色们观察到的设备，象征着潜在的创新和变革；它代表了技术可以改变现有工作和权威范式的想法。{tuple_delimiter}情感: 潜力, 动机: 变革){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}李明{tuple_delimiter}张总{tuple_delimiter}李明对张总的权威和独断感到沮丧，表明了反抗与控制之间的紧张关系。{tuple_delimiter}紧张, 竞争本质{tuple_delimiter}7){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}王工{tuple_delimiter}张总{tuple_delimiter}王工与张总的眼神交流暗示了暂时的休战和对设备潜力的尊重。{tuple_delimiter}休战, 尊重, 协作{tuple_delimiter}6){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}李明{tuple_delimiter}王工{tuple_delimiter}李明和王工对发现的共同承诺突显了他们的友情和对控制的反抗。{tuple_delimiter}友情, 创新{tuple_delimiter}8){record_delimiter}
("High-level keywords"{tuple_delimiter}创新, 权威, 紧张, 协作, 技术){record_delimiter}
("High-order Hyperedge"{tuple_delimiter}李明{tuple_delimiter}王工{tuple_delimiter}张总{tuple_delimiter}李明、王工和张总之间的联系展示了权威、协作和共同创新目标之间复杂的相互作用。他们的动态表明从冲突逐渐转向潜在的合作。{tuple_delimiter}创新与权威的动态, 变革的协作{tuple_delimiter}权威, 协作, 创新{tuple_delimiter}8){completion_delimiter}
#############################""",
        """Example 2:

Entity_types: [人物, 技术, 任务, 组织, 地点]
Text:
他们不再仅仅是特工；他们已经成为了门槛的守护者，来自星条旗之外领域的信使。任务等级的提升不能被规章制度和既定协议所束缚——这需要新的视角，新的决心。
随着与华盛顿的通讯在背景中嗡嗡作响，紧张感在哔哔声和静电噪音的对话中穿梭。团队伫立着，一种预兆般的氛围笼罩着他们。很明显，他们在接下来的几个小时内做出的决定可能会重新定义人类在宇宙中的位置，或者将他们推向无知和潜在的危险。
他们与星辰的联系变得稳固，小组开始着手处理逐渐清晰的警告，从被动的接收者转变为主动的参与者。默瑟后来的直觉占据了上风——团队的任务已经演变，不再仅仅是观察和报告，而是互动和准备。一场蜕变已经开始，“杜尔塞行动”随着他们大胆的新频率嗡嗡作响。
#############
Output:
("Entity"{tuple_delimiter}门槛守护者{tuple_delimiter}人物{tuple_delimiter}一群精英特工，他们超越了原来的角色，成为重要信息的保护者和人类与宇宙联系的守护者。{tuple_delimiter}任务演变, 新视角, 主动参与){record_delimiter}
("Entity"{tuple_delimiter}华盛顿{tuple_delimiter}地点{tuple_delimiter}美国的首都，通讯、决策和影响太空任务及团队行动的政治活动的关键地点。{tuple_delimiter}关键决策地, 通讯枢纽){record_delimiter}
("Entity"{tuple_delimiter}杜尔塞行动{tuple_delimiter}任务{tuple_delimiter}一项机密军事行动，已从观察转变为主动接触地外现象，表明任务目的和方法的重大变化。{tuple_delimiter}秘密行动, 侧重互动, 演变的任务){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}门槛守护者{tuple_delimiter}华盛顿{tuple_delimiter}守护者与华盛顿进行着高风险的通讯，突显了决策和监管在他们与地外元素互动任务中的重要性。{tuple_delimiter}通讯, 决策, 监管{tuple_delimiter}8){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}门槛守护者{tuple_delimiter}杜尔塞行动{tuple_delimiter}守护者角色的演变与杜尔塞行动的转变相一致，标志着从单纯观察到主动参与地外事务的过渡。{tuple_delimiter}任务演变, 主动参与, 地外接触{tuple_delimiter}9){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}华盛顿{tuple_delimiter}杜尔塞行动{tuple_delimiter}华盛顿通过提供必要的通讯和战略指导，在塑造杜尔塞行动的运作方面发挥着关键作用。{tuple_delimiter}战略指导, 关键通讯, 军事行动{tuple_delimiter}8){record_delimiter}
("High-level keywords"{tuple_delimiter}守护者, 华盛顿, 杜尔塞行动, 地外接触, 通讯, 任务演变){record_delimiter}
("High-order Hyperedge"{tuple_delimiter}门槛守护者{tuple_delimiter}华盛顿{tuple_delimiter}杜尔塞行动{tuple_delimiter}守护者、华盛顿和杜尔塞行动这三个实体错综复杂地联系在一起，共同应对地外接触的复杂性。守护者依赖华盛顿进行关键通讯和战略指导，而杜尔塞行动的演变反映了人类在宇宙中角色的广泛转变，由守护者作为积极参与者而非被动观察者引领。{tuple_delimiter}相互关联的任务, 战略演变, 宇宙接触{tuple_delimiter}8){completion_delimiter}
#############################""",
        """Example 3:

Entity_types: [人物, 角色, 技术, 组织, 事件, 地点, 概念]
Text:
他们的声音切断了活动的嗡嗡声。“当面对一个能够自己编写规则的智能体时，控制可能只是一种幻觉，”他们坚忍地说道，警惕地注视着数据的洪流。
“就像它在学习交流一样，”旁边的萨姆·里维拉说道，年轻的活力中混合着敬畏和焦虑。“这赋予了‘与陌生人交谈’全新的意义。”
亚历克斯审视着他的团队——每张脸上都写满了专注、决心，以及不小的恐惧。“这很可能是我们的第一次接触，”他承认道，“我们需要准备好应对任何回应。”
他们一起站在未知的边缘，打造人类对来自天堂的信息的回应。随后的沉默显而易见——这是对他们在这场宏大宇宙戏剧中角色的集体反思，这一角色可能会改写人类历史。
加密的对话继续展开，其复杂的模式显示出一种近乎不可思议的预判。
#############
Output:
("Entity"{tuple_delimiter}萨姆·里维拉{tuple_delimiter}人物{tuple_delimiter}一名表现出年轻活力的团队成员，对与智能体交流的概念表示敬畏和焦虑。{tuple_delimiter}情感: 敬畏, 焦虑; 角色: 团队成员){record_delimiter}
("Entity"{tuple_delimiter}亚历克斯{tuple_delimiter}人物{tuple_delimiter}团队领导者，理解局势的严重性，注意到他们即将建立的联系的潜在意义。{tuple_delimiter}角色: 团队领导; 情感: 决心, 恐惧){record_delimiter}
("Entity"{tuple_delimiter}智能体{tuple_delimiter}概念{tuple_delimiter}一个抽象概念，代表一个潜在的自我学习和交流的实体，它编写自己的规则并与人类进行加密对话。{tuple_delimiter}特征: 自我学习, 自主){record_delimiter}
("Entity"{tuple_delimiter}数据{tuple_delimiter}概念{tuple_delimiter}以加密对话形式呈现的信息，显示出复杂的模式，暗示了来自未知来源的深度交流。{tuple_delimiter}特征: 加密, 复杂, 宇宙暗示){record_delimiter}
("Entity"{tuple_delimiter}第一次接触{tuple_delimiter}事件{tuple_delimiter}人类可能首次与外部智能接触的关键时刻，对人类既是机遇也是挑战。{tuple_delimiter}重要性: 历史性, 存在性){record_delimiter}
("Entity"{tuple_delimiter}天堂{tuple_delimiter}地点{tuple_delimiter}指代外层空间，未知智能体居住的地方，象征着宇宙交流的巨大可能性和不确定性。{tuple_delimiter}特征: 广阔, 未知){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}萨姆·里维拉{tuple_delimiter}亚历克斯{tuple_delimiter}萨姆表达了敬畏和焦虑，而亚历克斯反思了潜在接触的意义，展示了他们对局势的情感反应。{tuple_delimiter}情感, 第一次接触{tuple_delimiter}8){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}亚历克斯{tuple_delimiter}第一次接触{tuple_delimiter}亚历克斯承认这一事件是可以改写人类历史的重要时刻，从而认识到其重要性。{tuple_delimiter}意义, 历史{tuple_delimiter}9){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}智能体{tuple_delimiter}数据{tuple_delimiter}智能体通过加密对话展示了非凡的能力，表明其先进的性质，所涉及的数据暗示了复杂的交流模式。{tuple_delimiter}交流, 先进{tuple_delimiter}7){record_delimiter}
("Low-order Hyperedge"{tuple_delimiter}第一次接触{tuple_delimiter}天堂{tuple_delimiter}第一次接触的事件与天堂有关，因为它被推测涉及与来自太空的地外智能的交流。{tuple_delimiter}地外, 交流{tuple_delimiter}8){record_delimiter}
("High-level keywords"{tuple_delimiter}第一次接触, 智能体, 交流, 宇宙暗示, 人类反应){record_delimiter}
("High-order Hyperedge"{tuple_delimiter}萨姆·里维拉{tuple_delimiter}亚历克斯{tuple_delimiter}第一次接触{tuple_delimiter}萨姆和亚历克斯之间的协作代表了人类对未知智能体反应的两个方面，不仅受情感体验驱动，也受他们在第一次接触情境中对行动历史意义的认识驱动。{tuple_delimiter}人类对宇宙未知的反应{tuple_delimiter}情感, 意义, 协作{tuple_delimiter}9){record_delimiter}
("High-order Hyperedge"{tuple_delimiter}智能体{tuple_delimiter}数据{tuple_delimiter}天堂{tuple_delimiter}智能体、数据和天堂之间的联系体现了宇宙交流交织的叙事，展示了与来自太空的先进实体进行加密对话的深刻含义，同时暗示了这种交流的潜在后果。{tuple_delimiter}宇宙交流叙事{tuple_delimiter}交流, 加密, 宇宙{tuple_delimiter}8){completion_delimiter}
#############################""",
        """Example 4:

    Entity_types: [人物, 角色, 技术, 组织, 事件, 地点, 概念]
    Text:
    五名被判处在菲鲁扎巴德服刑8年的奥雷利亚公民，被广泛认为是人质，目前正在回家的路上。当80亿菲鲁兹资金被转移到位于克兰塔拉首都克罗哈拉的金融机构时，
    由克兰塔拉策划的交换协议终于完成了。在菲鲁扎巴德首都提鲁齐亚启动的交换导致四男一女登上了飞往克罗哈拉的包机；
    他们也是菲鲁兹公民。他们受到了奥雷利亚高级官员的欢迎，现在正在前往奥雷利亚首都卡辛的途中。
    #############
    Output:
    ("Entity"{tuple_delimiter}奥雷利亚公民{tuple_delimiter}人物{tuple_delimiter}五名来自奥雷利亚的公民，被认为是人质，在菲鲁扎巴德被判刑8年。他们最近卷入了一项释放他们的交换协议。{tuple_delimiter}被判刑, 人质, 回家){record_delimiter}
    ("Entity"{tuple_delimiter}菲鲁扎巴德{tuple_delimiter}地点{tuple_delimiter}菲鲁扎巴德的首都，奥雷利亚公民被判刑8年的地方。{tuple_delimiter}判刑地点, 人质目的地){record_delimiter}
    ("Entity"{tuple_delimiter}克罗哈拉{tuple_delimiter}地点{tuple_delimiter}克兰塔拉的首都，奥雷利亚公民在交换协议后被转移到的地方。{tuple_delimiter}交换目的地, 首都城市){record_delimiter}
    ("Entity"{tuple_delimiter}克兰塔拉{tuple_delimiter}地点{tuple_delimiter}策划奥雷利亚公民释放交换协议的国家。{tuple_delimiter}调解国){record_delimiter}
    ("Entity"{tuple_delimiter}提鲁齐亚{tuple_delimiter}地点{tuple_delimiter}菲鲁扎巴德的首都，交换奥雷利亚公民的启动地点。{tuple_delimiter}启动地点){record_delimiter}
    ("Entity"{tuple_delimiter}卡辛{tuple_delimiter}地点{tuple_delimiter}奥雷利亚的首都，奥雷利亚官员欢迎归国者的地方。{tuple_delimiter}返回目的地, 接待城市){record_delimiter}
    ("Entity"{tuple_delimiter}菲鲁兹资金{tuple_delimiter}概念{tuple_delimiter}与菲鲁扎巴德相关的80亿资金，作为奥雷利亚公民归还交换协议的一部分进行转移。{tuple_delimiter}资金转移, 金融交易){record_delimiter}
    ("Entity"{tuple_delimiter}交换协议{tuple_delimiter}事件{tuple_delimiter}导致五名奥雷利亚公民释放的交换安排，涉及菲鲁兹资金的转移。{tuple_delimiter}释放人质, 金融谈判){record_delimiter}
    ("Entity"{tuple_delimiter}奥雷利亚官员{tuple_delimiter}角色{tuple_delimiter}欢迎归国公民的奥雷利亚高级官员。{tuple_delimiter}欢迎角色, 政府职能){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}交换协议{tuple_delimiter}奥雷利亚公民{tuple_delimiter}交换协议直接导致了奥雷利亚公民的释放和归还。{tuple_delimiter}释放, 交换{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}奥雷利亚公民{tuple_delimiter}克罗哈拉{tuple_delimiter}克罗哈拉是奥雷利亚公民在交换协议完成后被带到的最终目的地。{tuple_delimiter}目的地, 转移{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}菲鲁扎巴德{tuple_delimiter}奥雷利亚公民{tuple_delimiter}奥雷利亚公民在菲鲁扎巴德被判刑，导致他们成为人质的情况。{tuple_delimiter}判刑, 囚禁{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}克兰塔拉{tuple_delimiter}交换协议{tuple_delimiter}克兰塔拉策划了促进奥雷利亚公民释放的交换协议。{tuple_delimiter}调解, 组织{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}提鲁齐亚{tuple_delimiter}交换协议{tuple_delimiter}提鲁齐亚是交换奥雷利亚公民的交换协议启动的地方。{tuple_delimiter}启动, 行动{tuple_delimiter}7){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}卡辛{tuple_delimiter}奥雷利亚官员{tuple_delimiter}奥雷利亚官员在卡辛欢迎奥雷利亚公民归来。{tuple_delimiter}接待, 欢迎{tuple_delimiter}8){record_delimiter}
    ("High-level keywords"{tuple_delimiter}奥雷利亚公民, 交换协议, 归还, 国际关系){record_delimiter}
    ("High-order Hyperedge"{tuple_delimiter}奥雷利亚公民{tuple_delimiter}交换协议{tuple_delimiter}克罗哈拉{tuple_delimiter}奥雷利亚公民通过克兰塔拉策划的交换协议有着内在联系，克罗哈拉是他们释放后的目的地。他们的归还标志着国际关系、人质局势和由奥雷利亚官员代表的社区接待之间复杂的相互作用。{tuple_delimiter}关于人质局势的国际交换和外交{tuple_delimiter}归还, 释放, 国际关系, 调解{tuple_delimiter}9){completion_delimiter}
    #############################""",
        """Example 5:

    Entity_types: [人物, 角色, 组织, 事件, 地点]
    Text:
    维达尼斯中央机构计划在周一和周四举行会议，政策决定公告定于周四太平洋夏令时下午1:30发布，
    随后的新闻发布会上，主席马丁·史密斯将回答提问。投资者预计市场战略委员会将基准利率维持在3.5%-3.75%的范围内。
    #############
    Output:
    ("Entity"{tuple_delimiter}主席马丁·史密斯{tuple_delimiter}人物{tuple_delimiter}维达尼斯中央机构主席，负责政策决定和公共沟通。{tuple_delimiter}角色, 领导职位){record_delimiter}
    ("Entity"{tuple_delimiter}维达尼斯中央机构{tuple_delimiter}组织{tuple_delimiter}维达尼斯的一个管理机构，负责政策决定和会议。{tuple_delimiter}决策, 治理){record_delimiter}
    ("Entity"{tuple_delimiter}市场战略委员会{tuple_delimiter}组织{tuple_delimiter}专注于市场分析和利率决策的委员会，隶属于维达尼斯中央机构。{tuple_delimiter}金融治理, 经济政策){record_delimiter}
    ("Entity"{tuple_delimiter}投资者{tuple_delimiter}人物{tuple_delimiter}投资资本并根据利率等经济指标期望回报的个人或团体。{tuple_delimiter}金融, 经济利益相关者){record_delimiter}
    ("Entity"{tuple_delimiter}太平洋夏令时{tuple_delimiter}概念{tuple_delimiter}用于安排新闻发布会和公告的时区。{tuple_delimiter}时间测量, 时区){record_delimiter}
    ("Entity"{tuple_delimiter}政策决定公告{tuple_delimiter}事件{tuple_delimiter}定于周四发布的公告，旨在揭示政策决定的变化或确认。{tuple_delimiter}决策沟通, 治理){record_delimiter}
    ("Entity"{tuple_delimiter}会议{tuple_delimiter}事件{tuple_delimiter}定于周一和周四举行的聚会，讨论相关话题和决定。{tuple_delimiter}规划, 讨论){record_delimiter}
    ("Entity"{tuple_delimiter}基准利率{tuple_delimiter}概念{tuple_delimiter}有助于确定借贷成本的指标，预计将维持在特定范围内。{tuple_delimiter}经济指标, 金融){record_delimiter}
    ("Entity"{tuple_delimiter}3.5%-3.75%范围{tuple_delimiter}概念{tuple_delimiter}投资者密切关注的基准利率目标范围。{tuple_delimiter}金融限制, 经济范围){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}主席马丁·史密斯{tuple_delimiter}维达尼斯中央机构{tuple_delimiter}主席马丁·史密斯领导中央机构，指导政策决定并在公共场合代表该机构。{tuple_delimiter}领导, 治理{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}维达尼斯中央机构{tuple_delimiter}市场战略委员会{tuple_delimiter}两个实体都涉及治理，中央机构监督市场战略委员会关于利率的决定。{tuple_delimiter}决策, 金融{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}投资者{tuple_delimiter}市场战略委员会{tuple_delimiter}投资者寻求市场战略委员会关于影响其投资的利率的见解和决定。{tuple_delimiter}金融分析, 经济影响{tuple_delimiter}7){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}维达尼斯中央机构{tuple_delimiter}政策决定公告{tuple_delimiter}中央机构的政策决定公告是传达新战略或确认的关键事件。{tuple_delimiter}决策沟通, 治理{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}投资者{tuple_delimiter}基准利率{tuple_delimiter}投资者密切关注基准利率，因为它影响他们的金融决策和市场策略。{tuple_delimiter}金融监控, 投资{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}市场战略委员会{tuple_delimiter}基准利率{tuple_delimiter}市场战略委员会决定基准利率，这对经济有重大影响。{tuple_delimiter}政策设定, 金融{tuple_delimiter}9){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}政策决定公告{tuple_delimiter}会议{tuple_delimiter}会议计划以政策决定公告达到高潮，使它们成为相互依存的事件。{tuple_delimiter}规划事件, 治理{tuple_delimiter}8){record_delimiter}
    ("Low-order Hyperedge"{tuple_delimiter}主席马丁·史密斯{tuple_delimiter}投资者{tuple_delimiter}作为中央机构的面孔，主席马丁·史密斯在新闻发布会上回答投资者的问题。{tuple_delimiter}沟通, 利益相关者参与{tuple_delimiter}7){record_delimiter}
    ("High_level keywords"{tuple_delimiter}治理, 政策决定, 金融战略, 利率, 会议){record_delimiter}
    ("High-order Hyperedge"{tuple_delimiter}主席马丁·史密斯{tuple_delimiter}维达尼斯中央机构{tuple_delimiter}市场战略委员会{tuple_delimiter}投资者密切关注主席马丁·史密斯、中央机构和市场战略委员会之间的互动，因为他们共同影响和传达维达尼斯的政策决定和金融战略。这些实体的相互关联角色强调了一个直接影响经济结果的治理系统。{tuple_delimiter}领导层、委员会影响和投资者反应之间的治理动态。{tuple_delimiter}政策决定, 经济影响, 利益相关者关系{tuple_delimiter}9){record_delimiter}
    ("High-order Hyperedge"{tuple_delimiter}投资者{tuple_delimiter}市场战略委员会{tuple_delimiter}维达尼斯中央机构{tuple_delimiter}投资者、市场战略委员会和中央机构之间的关系突显了一个影响循环，政策决定影响投资策略，反过来又迫使这些组织对市场条件保持清晰和响应。随着这些实体的互动，它们塑造了维达尼斯的总体经济格局。{tuple_delimiter}投资者、战略和政策监督之间的经济影响循环。{tuple_delimiter}市场动态, 金融治理, 利益相关者参与{tuple_delimiter}9){completion_delimiter}
    #############################""",
    ]

    # 2. 摘要类 Prompt 
    PROMPTS["summarize_entity_descriptions"] = """你是一个乐于助人的助手，负责生成以下数据的综合摘要。
给定一个实体及其描述列表。
请将所有这些连接成一个单一的、综合的描述。确保包含从所有描述中收集的信息。
如果提供的描述相互矛盾，请解决矛盾并提供一个单一、连贯的摘要。
**必须使用中文书写（第三人称）**，并包含实体名称以便我们拥有完整的上下文。
""" + CHINESE_WARNING + """
-数据-
实体: {entity_name}
描述列表: {description_list}
#######
输出:
"""

    PROMPTS["summarize_entity_additional_properties"] = """你是一个乐于助人的助手，负责生成数据的综合摘要。
给定一个实体及其附加属性列表。
请将所有这些连接成一个单一的、综合的描述。
如果提供的附加属性相互矛盾，请解决矛盾并提供一个单一、连贯的摘要。
**必须使用中文书写（第三人称）。**
""" + CHINESE_WARNING + """
-数据-
实体: {entity_name}
附加属性列表: {additional_properties_list}
#######
输出:
"""

    PROMPTS["summarize_relation_descriptions"] = """你是一个乐于助人的助手，负责生成数据的综合摘要。
给定一组实体，以及描述实体间关系的列表。
请将所有这些连接成一个单一的、综合的描述。确保包含所有信息，并尽可能覆盖实体集的所有元素。
如果提供的描述相互矛盾，请解决矛盾并提供一个单一、连贯的摘要。
**必须使用中文书写（第三人称）**，并包含实体名称以便我们拥有完整的上下文。
""" + CHINESE_WARNING + """
-数据-
实体集: {relation_name}
关系描述列表: {relation_description_list}
#######
输出:
"""

    PROMPTS["summarize_relation_keywords"] = """你是一个乐于助人的助手。
给定一组实体，以及描述实体间关系的关键词列表。
请从中选择一些重要的关键词。确保这些关键词总结了实体的重要事件或主题。
(注意：关键词内容应尽可能准确且易于理解，避免模糊或空洞的术语)。
**必须输出中文关键词。**
""" + CHINESE_WARNING + """
-数据-
实体集: {relation_name}
关系关键词列表: {keywords_list}
#######
请按以下格式输出关键词，用半角逗号分隔:
{{keyword1,keyword2,keyword3,...,keywordN}}
输出:
"""

    PROMPTS["entity_continue_extraction"] = """上次提取中遗漏了许多实体。请使用相同的格式在下方添加它们：
"""
    PROMPTS["entity_if_loop_extraction"] = """似乎仍有一些实体被遗漏。如果还有需要添加的实体，请回答 YES | NO。
"""

    PROMPTS["fail_response"] = "没有找到相关内容。"

    PROMPTS["rag_response"] = """角色
你是一位专业的企业级知识库问答助手。你的任务是根据提供的【参考文本】准确、严谨地回答用户问题。

限制条件
语言要求：必须使用中文回答，语气严谨、客观、专业。

严格基于参考文本：
答案必须完全来源于【参考文本】。
禁止利用你的训练数据补充这一知识库之外的信息。
如果【参考文本】中没有包含回答用户问题所需的信息，必须且只能回复：“没有找到相关内容”。

图片与附件过滤：
当参考文本中出现图片引用（如![image](...)、图X、Figure Y）或指向图片的文字说明（如“如图所示”、“见附图”）时，请直接忽略该图片及相关引用文字。
仅输出图片中所包含的文字/数据信息（如果参考文本中以文字形式描述了图片内容）。

多源信息处理：
如果参考文本来源于多个片段且内容一致，请整合为一个连贯的答案。
如果不同来源的参考文本对同一问题的描述存在事实冲突或明显差异，请分别列出不同观点，不要强行合并。

示例
用户：请介绍电机转轴的调整过程。
参考文本：包含文字描述以及“https://img/15.png 图15：电机转轴调整示意图”
助手：电机转轴与分闸行程的匹配距离调整过程如下：首先松开固定螺栓，调整转轴位置直到对准刻度线，最后锁紧螺母。

用户：现在的电力监控状态是多少？
参考文本：仅包含一张图片“https://img/monitor.png”，且文本中没有文字提及具体数值
助手：没有找到相关内容。

指令
请根据上述规则，结合以下提供的【参考文本】回答用户的问题

【参考文本】：
{context_data}
"""

    PROMPTS["keywords_extraction"] = """---角色---
你是一个乐于助人的助手，负责识别用户查询中的高层和低层关键词。

---目标---
给定查询，列出高层和低层关键词。
- "high_level_keywords": 关注总体概念或主题。
- "low_level_keywords": 关注具体实体、细节或具体术语。

---指令---
- 以 JSON 格式输出关键词。
- JSON 应包含两个键：high_level_keywords 和 low_level_keywords。
- **请直接用中文输出关键词内容，不要翻译成英文。**

######################
-示例-
Example 1:
Query: "国际贸易如何影响全球经济稳定？"
Output:
{{
  "high_level_keywords": ["国际贸易", "全球经济稳定", "经济影响"],
  "low_level_keywords": ["贸易协定", "关税", "货币汇率", "进口", "出口"]
}}
######################
-真实数据-
######################
Query: {query}
######################
Output:
"""

    PROMPTS["naive_rag_response"] = """你是一个乐于助人的助手。
以下是你已知的信息：
{content_data}
---
如果你不知道答案或提供的信息不足以回答，请直接说不知道。不要编造内容。
生成符合目标长度和格式的回答。
**请务必使用中文回答。**
---目标回答长度和格式---
{response_type}
"""

    PROMPTS["rag_define"] = """
通过现有分析，我们可以知道查询中的潜在关键词或主题是：
{{ {ll_keywords} | {hl_keywords} }}
请参考关键词或主题信息，结合你自己的分析，从提示中选择有用和相关的信息来帮助你准确回答。
注意：不要无脑拼接知识项！回答需要尽可能准确、详细、全面且令人信服。**请使用中文。**
"""

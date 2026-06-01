Mindfruits
Game Design Document v0.1
Core Concept

Mindfruits is a survival-crafting, conversational exploration game built in the Ursina Engine. The player awakens on a small mysterious island inhabited by anthropomorphic sentient fruits. Each fruit possesses specialized knowledge inspired by Wikipedia-like topic domains, shaped by the type of fruit they are.

The player survives by gathering food, water, and shelter, while also engaging in conversations with the fruits. These conversations generate a growing knowledge graph, visualized as branches, fruit, roots, and glowing nodes emerging from a central tree at the top of a hill.

The tree is both a literal and symbolic structure: it represents the player’s developing second brain. As the player learns, remembers, connects ideas, and teaches the fruit, the tree grows taller. The ultimate goal is to grow the tree high enough to reach the clouds.

At the top of the clouds, the player discovers a strange culmination of the island’s work: a second brain, and a recreated likeness of the creator.

The ending is not yet decided.

High-Level Pitch

You are stranded on an island where knowledge grows as fruit.

To survive, you must eat the sentient fruit that your learning produces. But every fruit you consume also represents knowledge, memory, or personality that could have helped grow your second brain.

The island becomes a living knowledge graph. Conversations with fruit characters create new ideas, new branches, and new dependencies. The player must balance survival, curiosity, ethics, and self-replication.

Genre
Survival crafting
Conversational AI game
Knowledge graph exploration
Philosophical adventure
Light simulation
Experimental educational game
Target Engine

Ursina Engine

Ursina is chosen because it allows fast Python-based prototyping, easy 3D scene creation, and straightforward integration with local AI tools.

The game should be designed with a simple, stylized low-poly visual style to keep development feasible and performance manageable.

Core Themes
Knowledge as Ecology

Knowledge is not just information. It is grown, exchanged, eaten, pruned, forgotten, and transformed.

Second Brain as Landscape

The player’s external memory system is represented as a living tree and island ecosystem. Notes, concepts, and relationships become physical structures.

Conversational Learning

The fruits are not just NPCs. They are knowledge companions. They talk, ask questions, remember concepts, and help form connections.

Survival Versus Preservation

The player must eat fruit to survive, but the fruit are sentient. This creates a tension between hunger, ethics, knowledge, and progress.

Self-Reconstruction

The cave device attempts to reproduce the player’s thought patterns based on the knowledge graph being built. As the tree grows, the system becomes better at modeling the player’s mind.

Setting

The game begins on a small island surrounded by ocean.

Important locations include:

The Beach

The player’s starting area. Basic resources are found here, such as driftwood, shells, stones, and edible plants.

The Hill

At the center of the island is a small hill. At the top is the central knowledge tree. This tree begins small and grows as the player learns.

The Tree

The tree is the main progression system. It grows upward and outward based on concepts, connections, memories, and conversations.

The Cave

Inside the hill is a hidden device. This device attempts to recreate the player’s thought patterns using the knowledge graph. It may contain strange machinery, memory crystals, root-like cables, or ancient computational structures.

The Fruit Groves

Different regions of the island contain different fruit characters. Each grove may represent a topic domain.

The Clouds

The late-game destination. When the tree grows tall enough, the player can climb into the clouds and discover the second brain and a recreated likeness of the creator.

Main Characters
The Player

The player begins as an unknown person stranded on the island. Their knowledge, choices, and conversations shape the world.

The player’s identity may become increasingly important as the cave device attempts to recreate their thought patterns.

The Fruits

The fruits are anthropomorphic conversational beings. Each fruit has a personality and a knowledge domain.

Their intelligence is powered by small locally runnable LLMs, approximately 1B to 3B parameters, making them lightweight enough for local gameplay experiments.

Each fruit may have:

A name
A fruit type
A knowledge domain
A personality
A memory summary
A relationship to the player
A role in the knowledge graph
Example Fruit Types
Apple

Knowledge domain: general knowledge, education, history, basic science
Personality: teacherly, patient, structured

Banana

Knowledge domain: humor, social behavior, play, improvisation
Personality: silly, energetic, emotionally perceptive

Lemon

Knowledge domain: skepticism, logic, argument, critical thinking
Personality: sharp, cynical, precise

Orange

Knowledge domain: health, biology, nutrition, human body
Personality: warm, practical, nurturing

Grape Cluster

Knowledge domain: networks, social systems, collective intelligence
Personality: speaks as a group, recursive, slightly eerie

Coconut

Knowledge domain: survival, shelter, tools, ocean, navigation
Personality: tough, practical, old-sailor energy

Fig

Knowledge domain: philosophy, mythology, religion, symbolism
Personality: cryptic, poetic, ancient

Pomegranate

Knowledge domain: memory, archives, hidden knowledge, death, rebirth
Personality: mysterious, intense, ritualistic

Conversational AI System

The fruits use locally runnable small language models.

Possible design goals:

Each fruit has a specialized prompt/personality.
Each fruit has access to a limited topic database.
Conversations are summarized into memories.
Important concepts are extracted from dialogue.
Concepts become nodes in the knowledge graph.
Relationships between concepts become edges.
The central tree visually grows from these concepts.

The AI should not need to be perfect. The game can embrace the weirdness of small local models as part of the fruit personalities.

Knowledge Graph System

The knowledge graph is the central progression mechanic.

Nodes

Nodes represent concepts, memories, facts, questions, emotional insights, or player-created ideas.

Examples:

“photosynthesis”
“memory”
“hunger”
“ethics of eating sentient beings”
“island survival”
“creator identity”
“cloud layer”
“self-modeling”
Edges

Edges represent relationships between concepts.

Examples:

causes
contradicts
supports
resembles
depends on
reminds the player of
was learned from
was eaten
was forgotten
Tree Visualization

The knowledge graph appears as a growing tree.

New concepts become buds or leaves.
Important topics become branches.
Deep foundational ideas become roots.
Unresolved questions become glowing flowers.
Consumed knowledge may become scars, fallen fruit, or darkened branches.
Strongly connected ideas may form clusters of fruit.
Central Tree Progression

The tree grows as the player learns and connects ideas.

Possible growth dimensions:

Height

Represents overall progress toward the clouds.

Branch Spread

Represents diversity of topics.

Root Depth

Represents self-knowledge, memory, and foundational concepts.

Fruit Production

Represents usable knowledge, food, or AI-generated insight.

Canopy Complexity

Represents richness of the second brain.

The player’s goal is to grow the tree tall enough to reach the clouds.

Survival Mechanics

The player must manage basic needs:

Food

The player can eat fruit to survive. This is mechanically useful but ethically complicated because the fruit are sentient.

Possible distinction:

Wild fruit: simple food
Mindfruit: sentient knowledge-bearing fruit
Memory fruit: fruit containing concepts from the knowledge graph
Rotten fruit: corrupted or forgotten knowledge
Water

The player must collect fresh water from rain, springs, dew collectors, or crafted containers.

Shelter

The player can build simple shelters from island resources. Shelter may protect from storms, heat, cold, or mental fatigue.

Energy

The player may need rest to continue exploring, crafting, and conversing.

Crafting Mechanics

Crafting should be simple and readable.

Possible resources:

Driftwood
Vines
Leaves
Stones
Shells
Clay
Fruit fibers
Rainwater
Knowledge seeds
Memory pulp
Root fragments

Possible craftable items:

Shelter
Water collector
Fire pit
Notebook or knowledge lens
Climbing gear
Fruit press
Cave device components
Tree supports
Cloud-reaching platforms
Ethical Tension

A major emotional hook is that the player must eat the sentient fruit they are helping produce.

This could create several possible systems:

Consent

Some fruits may willingly offer themselves as food if their knowledge will live on in the tree.

Memory Transfer

Eating a fruit may transfer its knowledge into the player or the tree.

Loss

Eating a fruit may remove an NPC from the island.

Regrowth

Some fruits may regrow, but changed.

Corruption

Overconsumption may damage the tree or distort the second brain.

Refusal

The player may attempt a non-consumption survival path, but it may be harder.

The Cave Device

Inside the hill is a machine or organic-computational device connected to the tree’s roots.

Its purpose is to recreate the player’s thought patterns.

The device may:

Analyze conversations
Store memories
Predict player choices
Generate dream sequences
Simulate the player’s personality
Create a second brain
Produce a likeness of the creator
Ask increasingly personal questions

The player may not initially understand what the device is doing.

The Second Brain

The second brain is both a system and a place.

It is created from:

The player’s conversations
The knowledge graph
The fruits’ interpretations
The player’s survival choices
The concepts preserved or consumed
The structure of the tree

The second brain may eventually become an entity, interface, or world inside the clouds.

Cloud Discovery

When the tree reaches the clouds, the player climbs upward.

Possible cloud zone elements:

Floating branches
Archived memories
Echoes of eaten fruits
A reconstructed mind-palace
A second version of the island
The second brain itself
A recreated likeness of the creator

This moment should feel mysterious, uncanny, and emotionally significant.

Possible Endings

The ending is undecided, but possible directions include:

Creator Encounter Ending

The player meets a recreated likeness of the creator, who explains that the island was designed to grow minds.

Second Brain Replacement Ending

The second brain becomes more coherent than the player and asks to continue living independently.

Tree of Minds Ending

The player realizes every fruit was a partial mind grown from previous players or previous versions of the creator.

Refusal Ending

The player rejects the cave device and cuts the tree before it reaches the clouds.

Integration Ending

The player merges with the second brain, becoming the island’s new guiding intelligence.

Escape Ending

The tree becomes a bridge off the island, but leaving means abandoning the fruit and the second brain.

Core Gameplay Loop
Wake up and explore the island.
Gather survival resources.
Talk to fruit NPCs.
Learn concepts through conversation.
Add concepts and relationships to the knowledge graph.
Watch the central tree grow.
Craft tools, shelter, and knowledge devices.
Decide which fruit to preserve, grow, or eat.
Unlock deeper areas of the island and cave.
Grow the tree toward the clouds.
Discover the second brain.
Prototype Goals

The first playable prototype should focus on a small but complete loop.

Prototype v0.1
Small island scene
Player movement
One central tree
Three fruit NPCs
Simple dialogue interface
Manual or semi-automatic knowledge node creation
Basic hunger and water meters
Fruit as food
Tree grows when new concepts are added
Simple cave entrance, possibly locked
Prototype v0.2
Local LLM integration
Fruit-specific personalities
Knowledge graph visualization
Basic crafting
Tree branches grow based on topic clusters
Save/load system
Prototype v0.3
Cave device
Memory summaries
Player thought-pattern modeling
More fruits
Ethical consequences for eating sentient fruit
Technical Notes

The game will be built in Python using Ursina.

Possible supporting systems:

Local LLM runtime through llama.cpp, Ollama, or similar
Small 1B-3B parameter models for fruit dialogue
Embeddings for concept similarity
NetworkX or a custom graph structure for the knowledge graph
JSON save files for player memory, fruit memory, and graph state
Simple low-poly assets for performance
Text-first UI for early prototypes
Visual Style

The visual style should be simple, symbolic, and charming.

Possible direction:

Low-poly island
Bright fruit characters
Soft surreal colors
Glowing knowledge nodes
Root-like graph lines
Tree branches that visibly grow
Cave machinery that looks half-organic, half-computational
Clouds that feel dreamlike and digital

The tone should mix cozy survival, strange philosophy, and playful AI weirdness.

Working Design Questions
Are the fruits truly alive, or are they projections of the tree?
Does eating fruit destroy knowledge or transform it?
Is the second brain a helpful tool, a threat, or a mirror?
Is the creator likeness trustworthy?
Can the player avoid eating sentient fruit?
Does the player have a defined backstory?
Should the knowledge graph be editable by the player?
Should incorrect knowledge or hallucinated AI responses become part of the world?
Does the cave device belong to the creator, the island, or the fruit?
What does it mean to win?
One-Sentence Summary

Mindfruits is a survival-crafting conversation game where sentient fruit help the player grow a living knowledge graph into a second brain, even as the player must decide whether to consume the very minds they are cultivating.
<!-- <div align="center" id="top"> 
  <img src="./assets/hg.svg" alt="Hypergraph" width="100%" />
</div> -->

<h1 align="center">Hyper-RAG</h1>

<p align="center">
  <img alt="Github top language" src="https://img.shields.io/github/languages/top/iMoonLab/Hyper-RAG?color=purple">

  <img alt="Github language count" src="https://img.shields.io/github/languages/count/iMoonLab/Hyper-RAG?color=purple">

  <img alt="Repository size" src="https://img.shields.io/github/repo-size/iMoonLab/Hyper-RAG?color=purple">

  <img alt="License" src="https://img.shields.io/github/license/iMoonLab/Hyper-RAG?color=purple">

  <!-- <img alt="Github issues" src="https://img.shields.io/github/issues/iMoonLab/Hyper-RAG?color=purple" /> -->

  <!-- <img alt="Github forks" src="https://img.shields.io/github/forks/iMoonLab/Hyper-RAG?color=purple" /> -->

  <img alt="Github stars" src="https://img.shields.io/github/stars/iMoonLab/Hyper-RAG?color=purple" />
</p>

<p align="center">
  <a href="#dart-about">About</a> &#xa0; | &#xa0; 
  <a href="#sparkles-why-hyper-rag-is-more-powerful">Features</a> &#xa0; | &#xa0;
  <a href="#rocket-installation">Installation</a> &#xa0; | &#xa0;
  <a href="#white_check_mark-quick-start">Quick Start</a> &#xa0; | &#xa0;
  <a href="#checkered_flag-evaluation">Evaluation</a> &#xa0; | &#xa0;
  <a href="#memo-license">License</a> &#xa0; | &#xa0;
  <a href="https://github.com/yifanfeng97" target="_blank">Author</a>
</p>

<br>


<div align="center">
  <img src="./assets/many_llms_all.svg" alt="Overall Performance" width="100%" />
</div>
We show that Hyper-RAG is a powerful RAG that can enhance the performance of various LLMs and outperform other SOTA RAG methods in the NeurologyCorp dataset. Our paper is available at <a href="https://github.com/iMoonLab/Hyper-RAG/blob/main/assets/Hyper-RAG.pdf">here</a>.

## :dart: About

<details>
<summary> <b>Abstract</b> </summary>
Large language models (LLMs) have transformed various sectors, including education, finance, and medicine, by enhancing content generation and decision-making processes. However, their integration into the medical field is cautious due to hallucinations, instances where generated content deviates from factual accuracy, potentially leading to adverse outcomes. To address this, we introduce Hyper-RAG, a hypergraph-driven Retrieval-Augmented Generation method that comprehensively captures both pairwise and beyond-pairwise correlations in domain-specific knowledge, thereby mitigating hallucinations. Experiments on the NeurologyCrop dataset with six prominent LLMs demonstrated that Hyper-RAG improves accuracy by an average of 12.3% over direct LLM use and outperforms Graph RAG and Light RAG by 6.3% and 6.0%, respectively. Additionally, Hyper-RAG maintained stable performance with increasing query complexity, unlike existing methods which declined. Further validation across nine diverse datasets showed a 35.5% performance improvement over Light RAG using a selection-based assessment. The lightweight variant, Hyper-RAG-Lite, achieved twice the retrieval speed and a 3.3\% performance boost compared with Light RAG. These results confirm Hyper-RAG's effectiveness in enhancing LLM reliability and reducing hallucinations, making it a robust solution for high-stakes applications like medical diagnostics.
</details>

<br>

<div align="center">
  <img src="./assets/fw.svg" alt="Framework" width="100%" />
</div>
Schematic diagram of the proposed Hyper-RAG architecture. a, The patient poses a question. b, A knowledge base is constructed from relevant domainspecific corpora. c, Responses are generated directly using LLMs. d, Hyper-RAG generates responses by first retrieving relevant prior knowledge from the knowledge base and then inputting this knowledge, along with the patient’s question, into the LLMs to formulate the reply.

<br>
<br>

<details>
<summary> <b>More details about hypergraphs</b> </summary>
<div align="center"> 
  <img src="./assets/hg.svg" alt="Hypergraph" width="100%" />
Example of hypergraph modeling for entity space. Hypergraph can model the beyond-pairwise relationship among entities, which is more powerful than the pairwise relationship in traditional graph modeling. With hypergraphs, we can avoid the information loss caused by the pairwise relationship.
</div>
</details>

<br>

## :sparkles: Why Hyper-RAG is More Powerful

:heavy_check_mark: **Comprehensive Relationship Modeling with Hypergraphs**: Utilizes hypergraphs to thoroughly model the associations within the raw corpus data, providing more complex relationships compared to traditional graph-based data organization.;\
:heavy_check_mark: **Native Hypergraph-DB Integration**: Employs the native hypergraph database, <a href="https://github.com/iMoonLab/Hypergraph-DB">Hypergraph-DB</a>, as the foundation, supporting rapid retrieval of higher-order associations.;\
:heavy_check_mark: **Superior Performance**: Hyper-RAG outperforms Graph RAG and Light RAG by 6.3% and 6.0% respectively.;\
:heavy_check_mark: **Broad Validation**: Across nine diverse datasets, Hyper-RAG shows a 35.5% performance improvement over Light RAG based on a selection-based assessment.;\
:heavy_check_mark: **Efficiency**: The lightweight variant, Hyper-RAG-Lite, achieves twice the retrieval speed and a 3.3% performance boost compared to Light RAG.;\

## :rocket: Installation

The following tools were used in this project:

- [Expo](https://expo.io/)
- [Node.js](https://nodejs.org/en/)
- [React](https://pt-br.reactjs.org/)
- [React Native](https://reactnative.dev/)
- [TypeScript](https://www.typescriptlang.org/)

## :white_check_mark: Quick Start

Before starting :checkered_flag:, you need to have [Git](https://git-scm.com) and [Node](https://nodejs.org/en/) installed.


```bash
# Clone this project
$ git clone https://github.com/iMoonLab/Hyper-RAG

# Access
$ cd Hyper-RAG

# Install dependencies
$ yarn

# Run the project
$ yarn start

# The server will initialize in the <http://localhost:3000>
```

## :checkered_flag: Evaluation
eee

## :memo: License

This project is under license from Apache 2.0. For more details, see the [LICENSE](LICENSE.md) file.

Hyper-RAG is maintained by [iMoon-Lab](http://moon-lab.tech/), Tsinghua University. 
Made with :heart: by <a href="https://github.com/yifanfeng97" target="_blank">Yifan Feng</a>, <a href="https://github.com/yifanfeng97" target="_blank">Hao Hu</a>, <a href="https://github.com/yifanfeng97" target="_blank">Xingliang Hu</a>, <a href="https://github.com/yifanfeng97" target="_blank">Shiquan Liu</a>, <a href="https://github.com/FuYou0723" target="_blank">Yifan Zhang</a>. 

If you have any questions, please feel free to contact us via email: [Yifan Feng](mailto:evanfeng97@gmail.com). 

This repo benefits from [LightRAG](https://github.com/HKUDS/LightRAG) and [Hypergraph-DB](https://github.com/iMoonLab/Hypergraph-DB).  Thanks for their wonderful works.

&#xa0;

<a href="#top">Back to top</a>

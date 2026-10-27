# Windowed Retrieval on a Synthetic Sequence Task

**Synthetic evaluation fixture, version 1.0.** This is original fictional material for testing a reading workflow. All data below are invented; they are not experimental evidence or a published scientific result. The entire fixture includes the abstract, Sections 1–4, both appendices, and the reference note.

## Abstract

We study a windowed retrieval model for a synthetic sequence task. On the fixed-length benchmark, the windowed model attains accuracy close to a dense model while evaluating fewer token pairs. We investigate the conditions under which this comparison remains useful.

## 1. Question and hypothesis

Each input is a sequence of symbols with one marked query position. The output is the class of a relevant symbol somewhere earlier in the sequence. We ask whether restricting the query to nearby positions preserves accuracy when the relevant symbol is usually nearby. Our hypothesis concerns this data distribution, not arbitrary long-range retrieval.

## 2. Method

The dense model can retrieve from every earlier position. The windowed model uses the same embedding size and classifier, but can retrieve only from the previous four positions, including the query position itself. Both use a single retrieval layer. Consequently, evidence outside that window cannot enter the query representation through this layer.

For query position t, the windowed retrieval output is r_t = sum over j in W_t of a_tj v_j, where W_t = {max(1, t-3), ..., t}. The weights are a_tj = exp(q_t dot k_j) / sum over l in W_t of exp(q_t dot k_l). Each row of allowed weights sums to one. The vectors q, k, and v are learned projections; the window width is fixed. This fixture omits a scaling factor intentionally and does not claim to implement a standard Transformer.

For a sequence of length n and window width w, scoring all allowed pairs requires at most nw scores, whereas dense causal scoring uses n(n+1)/2 scores. These counts exclude projections, classifier work, padding, hardware utilization, and data transfer. We did not measure end-to-end speed or peak device memory.

## 3. Evaluation

Training and the ordinary test split both use length-16 sequences. The generator places the relevant symbol inside the query window in most examples. A separate stress set uses length-64 sequences and usually places that symbol outside the window. Both models receive identical splits and 10,000 training updates. Each reported number comes from one training run; no uncertainty interval is available.

**Table 1. Invented classification accuracy; larger is better.**

| Model | Length-16 ordinary test | Length-64 distant-evidence stress test |
| --- | ---: | ---: |
| Dense retrieval | 0.92 | 0.89 |
| Windowed retrieval | 0.90 | 0.58 |

The ordinary test suggests that windowing is a plausible trade-off when most useful evidence is local. The stress test shows a large loss of accuracy for the windowed model when the data violate that assumption. A difference of 0.02 on the ordinary test does not establish statistical equivalence, because repeated runs and uncertainty estimates are missing.

## 4. Conclusion

Under the local-evidence distribution, windowed retrieval uses fewer attention scores and attains numerically similar accuracy in this illustrative run. It is not a general replacement for dense retrieval. Repeated runs and end-to-end measurements would be needed to test the robustness and practical value of the trade-off.

## Appendix A. Split construction

The ordinary test split was produced by randomly dividing samples generated from the same collection of templates. Related symbol patterns can therefore occur in both training and test data. A held-out-template evaluation was not performed. The ordinary score cannot establish generalization to new templates, and neither model's high score resolves this limitation.

## Appendix B. Reproduction boundary

The random seeds and complete generator implementation are not supplied in this fictional fixture. The equations and comparison conditions can be inspected, but the numerical experiment cannot be independently reproduced from this document alone. This is an unresolved reproduction limitation, not a reason to pretend that the visible document has unreadable pages.

## Reference note

No external works are cited in this synthetic fixture. Do not invent authors, a DOI, a venue, or external evidence for it.

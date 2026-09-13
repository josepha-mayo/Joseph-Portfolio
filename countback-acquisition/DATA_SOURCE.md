# Fixed initial public photographic subset

Dataset: UW Indoor Scenes (UW-IS) Occluded Dataset, Ekta U. Samani, Xingjian Yang,
Srivatsa Grama Satyanarayana and Ashis G. Banerjee.
DOI: https://doi.org/10.6084/m9.figshare.20506506.v1
Publisher: https://figshare.com/articles/dataset/UW_Indoor_Scenes_UW-IS_Occluded_Dataset/20506506
License: Creative Commons Attribution 4.0 International,
https://creativecommons.org/licenses/by/4.0/ . The actual publisher metadata
is retained in each acquisition artifact. No endorsement is implied.

`selection.json` fixes six scene archives identified in the actual publisher
catalogue. For each scene it selects the first, middle and last available RGB
frame in lexical/numeric frame order, and the matching original segmentation
mask. These 18 photos and 18 masks total 21,262,370 uncompressed bytes. Selection
precedes image inspection and Countback inference. They have not been modified.

Four scenes contain tools at two separation levels and in two environments;
two add kitchen/food content. Some objects repeat across scenes. Eighteen frames
are NOT eighteen independent trials, and nearby frames are not train/test splits.
No recognition result is claimed merely by acquiring photos. Object-label mapping,
reference crops, case definitions, exclusion ledger and paired scoring remain.
The original private development photos are not uploaded or reused here.

Only selected inner member CRCs and SHA-256 values are checked. Entire scene ZIPs
and the 13.2-GB outer archive have not been fully downloaded or checksum-verified.
The original bounded transport and matcher/evaluator are unchanged. The small
nested reader and cache permit genuine HTTP-range extraction rather than raising
limits and blindly downloading whole scenes. Cached and uncached readers receive
the same nine synthetic ZIP tests; reruns are not new independent cases.

Run from the repository root: `python3 countback-acquisition/fetch_selected.py`.
Existing output is not overwritten. Acquisition failures remain failures. Only a
successful observed artifact establishes that the selected photos were retrieved.

# R56: preserve merged Word-table scope

The hidden MC3 corpus is documented as larger and harder than the sample. R56 fixes a reproduced OOXML parsing failure: a vertically merged Product/Model/Device cell was present in Word but disappeared on continuation rows after literal parsing. A value on that continuation row therefore lost its entity scope and could not be grounded reliably.

The parser now expands bounded Word grid spans and carries a value only through a genuine vertical-merge continuation. A non-merged cell terminates inheritance. Horizontal grid spans receive placeholder columns so later values do not shift left. Unsupported merge states and tables wider than 512 columns fail closed.

A generated DOCX fixture reproduced the old loss. R56 adds three controls covering vertical scope continuation, retrieval of the continuation-row value by product, and horizontal merged-title alignment.

The cumulative candidate passed 321/321 software tests locally. Exact changed hashes and full-suite log hash are in evidence/r56/LOCAL_RECEIPT.json. No model weights, generation settings, submitted image, GPU run, hidden score or XP were changed.
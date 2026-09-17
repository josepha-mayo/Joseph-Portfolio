# Counterstep: repair and transfer record

Focus: Distribute to every term. Selection: neural suggestion. Exercise seed: 490028.

## Original work

3(x + 2) = 12
3x + 2 = 12
x = 2

## Repair

Status: Correct after feedback, no hint or worked step
Help requested on this card: none.

Response 1:
3(x + 2) = 12
3x + 2 = 12
x = 2
Check: changed_solution. Line 2 still changes the solution set. Repair that transition next.

Response 2:
3(x + 2) = 12
3x+6=12
Check: unfinished. The steps agree. Continue until x is isolated on one side.

Response 3:
3(x + 2) = 12
3x+6=12
3x=6
x=2
Check: repaired. The repaired chain preserves the original solution and isolates x.

## Write the next step

Status: Completed with help
Help requested on this card: hint, reveal.

Question: 5(x + 7) = 55
Requested operation: Expand the bracket. Keep all terms and do not solve for x yet.

Response 1:
x=4
Check: different_operation. Same solution set, but not the requested step. Complete the operation above, rather than copying the question or jumping ahead.

Response 2:
5x + 35 = 55
Check: requested_step. The requested step is correct. Every term and the solution set are preserved.

## Changed-structure check

Status: Correct after feedback, no hint or worked step
Help requested on this card: none.

Question: 270 = 6(7x - 4)
Requested operation: Expand the bracket on the right. Do not solve for x yet.

Response 1:
<img src=x onerror=alert(1)>
Check: unsupported. Each line must contain exactly one equals sign.

Response 2:
270 = 42x - 24
Check: requested_step. The requested step is correct. Every term and the solution set are preserved.

## Interpretation
Only the equations and requested forms are checked. No inference about unwritten reasoning or lasting learning. These labels describe responses on individual cards, not mastery. The practice generators and weights are in the open-source application; this is not an exam or authenticated grade. The record can be edited by its holder. No identity or classroom data is required.
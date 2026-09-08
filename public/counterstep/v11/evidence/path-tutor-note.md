# Counterstep: repair and transfer record

Focus: Distribute to every term. Selection: neural suggestion. Exercise seed: 786665.

## Original work

~~~
3(x + 2) = 12
3x + 2 = 12
x = 2
~~~

## Repair

Status: Correct after feedback, no hint or worked step
Help requested on this card: none.

Response 1:
~~~
3(x + 2) = 12
3x + 2 = 12
x = 2
~~~
Check: changed_solution. Line 2 still changes the solution set. Repair that transition next.

Response 2:
~~~
3(x + 2) = 12
3x+6=12
~~~
Check: unfinished. The steps agree. Continue until x is isolated on one side.

Response 3:
~~~
3(x + 2) = 12
x*x=4
~~~
Check: unsupported. Line 2: Nonlinear products such as x*x are outside this version.

Response 4:
~~~
3(x + 2) = 12
3x+6=12
3x=6
x=2
~~~
Check: repaired. The repaired chain preserves the original solution and isolates x.

## Write the next step

Status: Completed with help
Help requested on this card: hint, reveal.

Question: 2(x + 3) = 12
Requested operation: Expand the bracket. Keep all terms and do not solve for x yet.

Response 1:
~~~
x=3
~~~
Check: different_operation. Same solution set, but not the requested step. Complete the operation above, rather than copying the question or jumping ahead.

Response 2:
~~~
2(x + 3) = 12
~~~
Check: different_operation. Same solution set, but not the requested step. Complete the operation above, rather than copying the question or jumping ahead.

Response 3:
~~~
2x + 6 = 12
~~~
Check: requested_step. The requested form is correct, and the solution set is preserved.

## Changed-structure check

Status: Correct on first response, no help on this card
Help requested on this card: none.

Question: 48 = 3(3x - 2)
Requested operation: Expand the bracket on the right. Do not solve for x yet.

Response 1:
~~~
48 = 9x - 6
~~~
Check: requested_step. The requested form is correct, and the solution set is preserved.

## Interpretation
Only the equations and requested forms are checked. No inference about unwritten reasoning or lasting learning. These labels describe responses on individual cards, not mastery. The practice generators and weights are in the open-source application; this is not an exam or authenticated grade. The record can be edited by its holder. No identity or classroom data is required.
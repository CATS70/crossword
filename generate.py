import sys
import numpy
import math
from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """

        for var, words in self.domains.items():
            to_be_removed = []
            for w in words:
                if len(w) != var.length:
                    to_be_removed.append(w)

            self.domains[var].difference_update(to_be_removed)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revision = False
        # get the overlaps
        overlaps = self.crossword.overlaps[(x, y)]
        word_v1 = self.domains[x]
        word_v2 = self.domains[y]

        if overlaps is not None:
            to_removed = []
            for w1 in word_v1:
                found = False
                for w2 in word_v2:
                    if w1[overlaps[0]] == w2[overlaps[1]]:
                        found = True
                        break
                if not found:
                    to_removed.append(w1)
            self.domains[x].difference_update(to_removed)
            if len(to_removed) != 0:
                revision = True

        return revision

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
            arcs = [var for var, a in self.crossword.overlaps.items() if a is not None]

        while len(arcs) != 0:
            arc = arcs[0]
            arcs.remove(arc)
            if self.revise(arc[0], arc[1]):
                if len(self.domains[arc[0]]) == 0:
                    return False
                else:
                    for var in self.crossword.neighbors(arc[0]):
                        if var != arc[1]:
                            arcs.append((var, arc[0]))

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        # Check if all variables are in the assignment
        if self.crossword.variables.difference(assignment.keys()):
            return False
        # # Check if each var is associated with only 1 word
        # for k, v in assignment.items():
        #     if len(v) != 1:
        #         return False

        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # check if value of each variable are distinct
        values = list(assignment.values())
        lst, counts = numpy.unique(values, return_counts=True)
        if not all(counts == 1):
            return False

        for var, val in assignment.items():

            # check length
            if len(val) != var.length:
                return False

            # check overlaping consistency
            for n in self.crossword.neighbors(var):
                r = self.crossword.overlaps[(var, n)]
                if n in assignment:
                    word_v2 = {assignment[n]}
                    for w2 in word_v2:
                        if val[r[0]] != w2[r[1]]:
                            return False
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        result = dict()
        word_var = self.domains[var]
        for n in self.crossword.neighbors(var):
            if n not in assignment:
                overlap = self.crossword.overlaps[var, n]
                words_neighbor = self.domains[n]
                for w1 in word_var:
                    nb_eliminated = 0
                    for w2 in words_neighbor:
                        if w1[overlap[0]] != w2[overlap[1]]:
                            nb_eliminated += 1
                            result[w1] = nb_eliminated

        if len(result) == 0:
            return word_var
        values_sorted = sorted(word_var, key=result.__getitem__)
        return values_sorted

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        # Get all variables not in the assignment

        uv = list(self.crossword.variables.difference(assignment.keys()))
        uv_sorted = {var: len(self.domains[var]) for var in uv}

        length = math.inf

        # Get fewest values domains
        for v, l in uv_sorted.items():
            if l < length:
                length = l
        v_candidate = [var for var, l in uv_sorted.items() if l == length]
        index = 0
        if len(v_candidate) != 1:

            n = len(self.crossword.neighbors(v_candidate[index]))
            for i in range(1, len(v_candidate)):
                if len(self.crossword.neighbors(v_candidate[i])) > n:
                    n = len(self.crossword.neighbors(v_candidate[i]))
                    index = i

        return v_candidate[index]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        var = self.select_unassigned_variable(assignment)
        ordered_value_var = self.order_domain_values(var, assignment)

        for v in ordered_value_var:
            assignment[var] = v
            if self.consistent(assignment):
                result = self.backtrack(assignment)
                if result is not None:
                    return result
                assignment.pop(var)
        return None


def main():
    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()

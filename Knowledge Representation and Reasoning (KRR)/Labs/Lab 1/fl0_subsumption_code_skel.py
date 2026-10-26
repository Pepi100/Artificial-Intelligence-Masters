"""
FL₀ Structural Subsumption Algorithm - Student Implementation

This module provides a skeleton for implementing structural subsumption
checking in the FL₀ Description Logic language.

FL₀ allows:
  - Concept names (atomic concepts)
  - Conjunction (⊓)
  - Universal restriction (∀R.C)
  - Top concept (⊤)

Student Task: Complete the verify_subsumption() function to check whether
concept C is subsumed by concept D (written C ⊑ D).

Recall: C ⊑ D means every instance of C is also an instance of D.
"""

from typing import List, Set, Dict, Optional
from dataclasses import dataclass


# ============================================================================
# CONCEPT REPRESENTATION CLASSES
# ============================================================================

@dataclass
class ConceptName:
    """
    Represents an atomic concept (concept name).
    
    Example: A, B, Student, Professor
    """
    name: str
    
    def __repr__(self):
        return self.name
    
    def __eq__(self, other):
        return isinstance(other, ConceptName) and self.name == other.name
    
    def __hash__(self):
        return hash(('ConceptName', self.name))


@dataclass
class TopConcept:
    """
    Represents the top concept (⊤), which is satisfied by all individuals.
    """
    
    def __repr__(self):
        return "⊤"
    
    def __eq__(self, other):
        return isinstance(other, TopConcept)
    
    def __hash__(self):
        return hash('TopConcept')


@dataclass
class BottomConcept:
    """
    Represents the bottom concept (⊥), which is satisfied by no individual.
    Note: ⊥ is not part of standard FL₀ but included for extensions.
    """
    
    def __repr__(self):
        return "⊥"
    
    def __eq__(self, other):
        return isinstance(other, BottomConcept)
    
    def __hash__(self):
        return hash('BottomConcept')


@dataclass
class UniversalRestriction:
    """
    Represents a universal restriction: ∀R.C
    
    Meaning: All R-successors must satisfy concept C.
    
    Args:
        role: The role name (R)
        filler: The concept that must be satisfied (C)
    
    Example: ∀teaches.GraduateCourse
    """
    role: str
    filler: 'Concept'
    
    def __repr__(self):
        filler = str(self.filler)

        if isinstance(self.filler, NormalForm):
            n = len(self.filler.concept_names) + len(self.filler.restrictions)
            if n > 1:
                filler = f"({filler})"
        elif isinstance(self.filler, Conjunction):
            filler = f"({filler})"

        return f"∀{self.role}.{filler}"
    
    def __eq__(self, other):
        return (isinstance(other, UniversalRestriction) and 
                self.role == other.role and 
                self.filler == other.filler)
    
    def __hash__(self):
        return hash(('UniversalRestriction', self.role, self.filler))


@dataclass
class Conjunction:
    """
    Represents a conjunction of concepts: C₁ ⊓ C₂ ⊓ ... ⊓ Cₙ
    
    Args:
        conjuncts: List of concepts that are conjoined
    
    Example: A ⊓ B ⊓ ∀R.C
    """
    conjuncts: List['Concept']
    
    def __repr__(self):
        if not self.conjuncts:
            return "⊤"
        return " ⊓ ".join(str(c) for c in self.conjuncts)
    
    def __eq__(self, other):
        return (isinstance(other, Conjunction) and 
                set(self.conjuncts) == set(other.conjuncts))
    
    def __hash__(self):
        return hash(('Conjunction', tuple(sorted(self.conjuncts, key=str))))


# Type alias for any concept
Concept = ConceptName | TopConcept | BottomConcept | UniversalRestriction | Conjunction


# ============================================================================
# NORMALIZATION HELPER
# ============================================================================

@dataclass
class NormalForm:
    """
    Represents a concept in FL₀ normal form:
    A₁ ⊓ A₂ ⊓ ... ⊓ Aₘ ⊓ ∀R₁.C₁ ⊓ ... ⊓ ∀Rₙ.Cₙ
    
    Args:
        concept_names: Set of atomic concept names
        restrictions: Dictionary mapping role names to their filler concepts (in normal form)
    """
    concept_names: Set[str]
    restrictions: Dict[str, 'NormalForm']
    
    def __repr__(self):
        parts = [ConceptName(name) for name in sorted(self.concept_names)]
        for role in sorted(self.restrictions.keys()):
            parts.append(UniversalRestriction(role, self.restrictions[role]))
        return " ⊓ ".join(str(p) for p in parts) if parts else "⊤"


def normalize(concept: Concept) -> NormalForm:
    """
    Converts an FL₀ concept into normal form.
    
    Normal form for FL₀:
      A₁ ⊓ ... ⊓ Aₘ ⊓ ∀R₁.C₁ ⊓ ... ⊓ ∀Rₙ.Cₙ
    
    where:
      - A₁, ..., Aₘ are distinct concept names
      - R₁, ..., Rₙ are distinct role names
      - C₁, ..., Cₙ are in normal form (recursively)
    
    Args:
        concept: An FL₀ concept to normalize
    
    Returns:
        NormalForm object representing the normalized concept
    """
    concept_names = set()
    restrictions = {}
    
    def merge_normal_forms(nf1: NormalForm, nf2: NormalForm) -> NormalForm:
        """
        Recursively merge two NormalForm objects representing a conjunction
        of constraints: equivalent to the normal form of (nf1 ⊓ nf2).

        - concept_names are unioned
        - for each role appearing in either nf1 or nf2, their fillers are
          recursively merged when both exist, otherwise copied over.
        """
        merged_names = set(nf1.concept_names) | set(nf2.concept_names)
        merged_restr = dict(nf1.restrictions)
        for role, filler in nf2.restrictions.items():
            if role in merged_restr:
                # recursive merge for nested fillers
                merged_restr[role] = merge_normal_forms(merged_restr[role], filler)
            else:
                merged_restr[role] = filler
        return NormalForm(merged_names, merged_restr)
    
    def process(c: Concept):
        """Recursively process a concept and extract components."""
        if isinstance(c, ConceptName):
            concept_names.add(c.name)
        
        elif isinstance(c, TopConcept):
            # Top concept adds no constraints
            pass
        
        elif isinstance(c, BottomConcept):
            # Bottom concept makes everything bottom (extension)
            concept_names.add("⊥")
        
        elif isinstance(c, UniversalRestriction):
            # Normalize the filler first
            filler_normal = normalize(c.filler)
            
            if c.role in restrictions:
                # Merge with existing restriction on same role
                # ∀R.C ⊓ ∀R.D = ∀R.(C ⊓ D)
                existing = restrictions[c.role]
                # Properly merge the two NormalForms
                restrictions[c.role] = merge_normal_forms(existing, filler_normal)
            else:
                restrictions[c.role] = filler_normal
        
        elif isinstance(c, Conjunction):
            # Process each conjunct
            for conjunct in c.conjuncts:
                process(conjunct)
    
    process(concept)
    return NormalForm(concept_names, restrictions)


# ============================================================================
# SUBSUMPTION CHECKING (STUDENT IMPLEMENTATION REQUIRED)
# ============================================================================

def verify_subsumption(C: Concept, D: Concept) -> bool:
    """
    Checks whether concept C is subsumed by concept D (C ⊑ D).
    
    Algorithm:
      1. Normalize both C and D
      2. Check two conditions:
         (i) Every concept name in D appears in C
         (ii) For every ∀R.D_i in D, there exists ∀R.C_j in C 
              such that C_j ⊑ D_i (recursive check)
    
    Args:
        C: The subsuming concept (more specific)
        D: The subsumed concept (more general)
    
    Returns:
        True if C ⊑ D, False otherwise
    
    STUDENT TASK: Implement this function!
    
    Hints:
      - Use the normalize() function to get normal forms
      - Check condition (i): concept names
      - Check condition (ii): role restrictions (recursive!)
      - Remember: C ⊑ D means C is MORE SPECIFIC than D
    """
    # TODO: Implement subsumption checking
    # 
    # Step 1: Normalize both concepts
    # nf_C = normalize(C)
    # nf_D = normalize(D)
    #
    # Step 2: Check condition (i) - concept names
    # ...
    #
    # Step 3: Check condition (ii) - role restrictions (recursive)
    # ...
    
    raise NotImplementedError("Students must implement this function!")


# ============================================================================
# TEST CASES
# ============================================================================

def test_problem_1():
    """
    TEST PROBLEM 1 (Simple - No role restrictions)
    
    Check: A ⊓ B ⊑ A
    
    Expected: True
    Reason: A ⊓ B is more specific than A (has additional constraint B)
    """
    print("\n" + "="*60)
    print("TEST PROBLEM 1: Simple concept name subsumption")
    print("="*60)
    
    # C = A ⊓ B
    C = Conjunction([ConceptName("A"), ConceptName("B")])
    
    # D = A
    D = ConceptName("A")
    
    print(f"Testing: {C} ⊑ {D}")
    print(f"C (normalized): {normalize(C)}")
    print(f"D (normalized): {normalize(D)}")
    
    try:
        result = verify_subsumption(C, D)
        expected = True
        print(f"\nResult: {result}")
        print(f"Expected: {expected}")
        print(f"Status: {'✓ PASS' if result == expected else '✗ FAIL'}")
    except NotImplementedError:
        print("\n⚠ Implementation required!")
    
    return expected


def test_problem_2():
    """
    TEST PROBLEM 2 (Simple role restriction)
    
    Check: A ⊓ ∀R.B ⊑ A
    
    Expected: True
    Reason: A ⊓ ∀R.B is more specific than A
    """
    print("\n" + "="*60)
    print("TEST PROBLEM 2: Concept with role restriction")
    print("="*60)
    
    # C = A ⊓ ∀R.B
    C = Conjunction([
        ConceptName("A"),
        UniversalRestriction("R", ConceptName("B"))
    ])
    
    # D = A
    D = ConceptName("A")
    
    print(f"Testing: {C} ⊑ {D}")
    print(f"C (normalized): {normalize(C)}")
    print(f"D (normalized): {normalize(D)}")
    
    try:
        result = verify_subsumption(C, D)
        expected = True
        print(f"\nResult: {result}")
        print(f"Expected: {expected}")
        print(f"Status: {'✓ PASS' if result == expected else '✗ FAIL'}")
    except NotImplementedError:
        print("\n⚠ Implementation required!")
    
    return expected


def test_problem_3():
    """
    TEST PROBLEM 3 (Multiple role restrictions)
    
    Check: A ⊓ ∀R.B ⊓ ∀R.C ⊑ ∀R.(B ⊓ C)
    
    Expected: True
    Reason: ∀R.B ⊓ ∀R.C means "all R-successors are B AND all R-successors are C"
            which is equivalent to ∀R.(B ⊓ C)
    
    CHALLENGE: Your normalization will merge ∀R.B and ∀R.C into ∀R.(B ⊓ C)
               Then you need to verify (B ⊓ C) ⊑ (B ⊓ C)
    """
    print("\n" + "="*60)
    print("TEST PROBLEM 3: Multiple restrictions on same role")
    print("="*60)
    
    # C = A ⊓ ∀R.B ⊓ ∀R.C
    C = Conjunction([
        ConceptName("A"),
        UniversalRestriction("R", ConceptName("B")),
        UniversalRestriction("R", ConceptName("C"))
    ])
    
    # D = ∀R.(B ⊓ C)
    D = UniversalRestriction("R", Conjunction([
        ConceptName("B"),
        ConceptName("C")
    ]))
    
    print(f"Testing: {C} ⊑ {D}")
    print(f"C (normalized): {normalize(C)}")
    print(f"D (normalized): {normalize(D)}")
    
    try:
        result = verify_subsumption(C, D)
        expected = True
        print(f"\nResult: {result}")
        print(f"Expected: {expected}")
        print(f"Status: {'✓ PASS' if result == expected else '✗ FAIL'}")
    except NotImplementedError:
        print("\n⚠ Implementation required!")
    
    return expected


def test_problem_4():
    """
    TEST PROBLEM 4 (Deep nesting with multiple paths)
    
    Check: ∀R.(A ⊓ ∀S.(B ⊓ C) ⊓ ∀T.D) ⊓ ∀R.∀S.C ⊑ ∀R.(∀S.B ⊓ ∀T.D)
    
    Expected: True
    
    Reasoning (complex!):
      - D requires ∀R.(∀S.B ⊓ ∀T.D)
      - C has ∀R.(A ⊓ ∀S.(B ⊓ C) ⊓ ∀T.D) 
      - C also has ∀R.∀S.C (which normalizes to ∀R.(∀S.C))
      - After normalization, C becomes: ∀R.(A ⊓ ∀S.(B ⊓ C) ⊓ ∀S.C ⊓ ∀T.D)
      - The ∀S restrictions merge: ∀S.(B ⊓ C) ⊓ ∀S.C → ∀S.(B ⊓ C)
      - So C = ∀R.(A ⊓ ∀S.(B ⊓ C) ⊓ ∀T.D)
      - Now check if (A ⊓ ∀S.(B ⊓ C) ⊓ ∀T.D) ⊑ (∀S.B ⊓ ∀T.D)
        * For ∀S.B: C has ∀S.(B ⊓ C), and (B ⊓ C) ⊑ B ✓
        * For ∀T.D: C has ∀T.D, and D ⊑ D ✓
    
    CHALLENGE: Deep recursion with multiple role paths and normalization complexity!
    """
    print("\n" + "="*60)
    print("TEST PROBLEM 4: Deep nested structure with multiple roles")
    print("="*60)
    
    # C = ∀R.(A ⊓ ∀S.(B ⊓ C) ⊓ ∀T.D) ⊓ ∀R.∀S.C
    C = Conjunction([
        UniversalRestriction("R", Conjunction([
            ConceptName("A"),
            UniversalRestriction("S", Conjunction([
                ConceptName("B"),
                ConceptName("C")
            ])),
            UniversalRestriction("T", ConceptName("D"))
        ])),
        UniversalRestriction("R", UniversalRestriction("S", ConceptName("C")))
    ])
    
    # D = ∀R.(∀S.B ⊓ ∀T.D)
    D = UniversalRestriction("R", Conjunction([
        UniversalRestriction("S", ConceptName("B")),
        UniversalRestriction("T", ConceptName("D"))
    ]))
    
    print(f"Testing: {C} ⊑ {D}")
    print(f"C (normalized): {normalize(C)}")
    print(f"D (normalized): {normalize(D)}")
    
    try:
        result = verify_subsumption(C, D)
        expected = True
        print(f"\nResult: {result}")
        print(f"Expected: {expected}")
        print(f"Status: {'✓ PASS' if result == expected else '✗ FAIL'}")
    except NotImplementedError:
        print("\n⚠ Implementation required!")
    
    return expected


def test_problem_5_negative():
    """
    TEST PROBLEM 5 (Negative case - should return False)
    
    Check: A ⊑ A ⊓ B
    
    Expected: False
    Reason: A is MORE GENERAL than A ⊓ B (subsumption goes the other way)
    """
    print("\n" + "="*60)
    print("TEST PROBLEM 5: Negative case (should fail subsumption)")
    print("="*60)
    
    # C = A
    C = ConceptName("A")
    
    # D = A ⊓ B
    D = Conjunction([ConceptName("A"), ConceptName("B")])
    
    print(f"Testing: {C} ⊑ {D}")
    print(f"C (normalized): {normalize(C)}")
    print(f"D (normalized): {normalize(D)}")
    
    try:
        result = verify_subsumption(C, D)
        expected = False
        print(f"\nResult: {result}")
        print(f"Expected: {expected}")
        print(f"Status: {'✓ PASS' if result == expected else '✗ FAIL'}")
    except NotImplementedError:
        print("\n⚠ Implementation required!")
    
    return expected


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":  
    print("\nRunning test problems...\n")
    
    # Run all test problems
    test_problem_1()
    test_problem_2()
    test_problem_3()
    test_problem_4()
    test_problem_5_negative()
    
    print("\n" + "="*60)
    print("All tests complete!")
    print("="*60)
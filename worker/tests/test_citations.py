"""ORCA's suggested citations: parsing the section at the end of an output."""

from hclust.citations import Collected, parse, render

TAIL = """
SUGGESTED CITATIONS FOR THIS RUN
--------------------------------

We neither can nor want to force you to cite these papers, but we appreciate if you do

List of essential papers. We consider these as the minimum necessary citations

  1. Neese, F.
     Software update: the ORCA program system, version 6.0
     WIRES Comput. Molec. Sci. 2025 15(1), e70019
     doi.org/10.1002/wcms.70019

List of papers to cite with high priority. The work reported in these papers was absolutely
necessary for this run to complete.
Our perspective: the developers of density functionals and basis sets usually get cited in chemistry papers

  1. Neese, F.
     An improvement of the resolution of the identity approximation for the formation of the Coulomb matrix
     J. Comp. Chem. 2003 24(14), 1740-1747
     doi.org/10.1002/jcc.10318
  2. Kossmann, S.; Neese, F.
     Comparison of two efficient approximate Hartee-Fock approaches
     Chem. Phys. Lett. 2009 481 , 240-243
     doi.org/10.1016/j.cplett.2009.09.073

List of optional additional citations

  1. Neese, F.
     Approximate second-order SCF convergence for spin unrestricted wavefunctions
     Chem. Phys. Lett. 2000 325(1-3), 93-98
     doi.org/10.1016/s0009-2614(00)00662-x

Timings for individual modules:

Sum of individual times          ...        0.393 sec (=   0.007 min)
"""


def test_parse_reads_every_group_and_entry():
    found = parse("lots of output\n" + TAIL)
    assert [(g, c.doi) for g, c in found] == [
        ("essential", "10.1002/wcms.70019"),
        ("high priority", "10.1002/jcc.10318"),
        ("high priority", "10.1016/j.cplett.2009.09.073"),
        ("optional", "10.1016/s0009-2614(00)00662-x"),
    ]
    essential = found[0][1]
    assert essential.authors == "Neese, F."
    assert essential.title == "Software update: the ORCA program system, version 6.0"
    assert essential.journal == "WIRES Comput. Molec. Sci. 2025 15(1), e70019"
    assert found[2][1].authors == "Kossmann, S.; Neese, F."


def test_parse_without_a_citation_section():
    assert parse("ORCA TERMINATED NORMALLY") == []


def test_render_groups_by_priority_with_users():
    [(g, essential), (_, ri)] = parse(TAIL)[:2]
    text = render([Collected(essential, g, {"CCSD(T)/aug-cc-pVTZ sp"}), Collected(ri, "high priority", {"wB97X-D4/def2-TZVPPD opt"})])
    assert text.index("## Essential") < text.index("## High priority")
    assert "[doi:10.1002/wcms.70019](https://doi.org/10.1002/wcms.70019)" in text
    assert "Used by: CCSD(T)/aug-cc-pVTZ sp" in text

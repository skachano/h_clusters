"""Phase 8 studies: extra calculations on a finished campaign's best structures.

Each study builds a set of keyed ORCA jobs from the campaign's analysis, runs them with the
same engine (content-addressed, cached, killable), stores them in the `study_result` table
and reports what they show.
"""

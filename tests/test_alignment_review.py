import torch

from err2text.alignment_review.runner import _ctc_viterbi, _labels_for_words, _separator_word_index
from err2text.sentence_boundary_review.runner import _internal_transitions, _prediction, _separator_word_index as baseline_separator_word_index


def test_ctc_viterbi_aligns_two_words_and_repeated_character() -> None:
    # blank=0; target A B B A with a word delimiter in the middle.
    logits = torch.tensor([
        [0.0, 7.0, 0.0, 0.0],  # A
        [7.0, 0.0, 0.0, 0.0],  # blank
        [0.0, 0.0, 0.0, 7.0],  # delimiter
        [0.0, 0.0, 7.0, 0.0],  # B
        [7.0, 0.0, 0.0, 0.0],  # blank separates repeated B
        [0.0, 0.0, 7.0, 0.0],  # B
        [0.0, 7.0, 0.0, 0.0],  # A
    ])
    aligned = _ctc_viterbi(logits, [1, 3, 2, 2, 1], blank_id=0)

    assert [label for label, _, _ in aligned] == [0, 1, 2, 3, 4]


def test_labels_and_separator_keep_estonian_words() -> None:
    vocab = {"a": 1, "õ": 2, "|": 3}
    labels, owners = _labels_for_words(["A", "ÕA"], vocab, "|")

    assert labels == [1, 3, 2, 1]
    assert owners == [0, None, 1, 1]
    words = [{"word": "Aga"}, {"word": "õige"}, {"word": "vastus"}]
    assert _separator_word_index(words, "Aga õige.") == 1


def test_sentence_boundary_baseline_uses_only_one_non_edge_transition() -> None:
    segment = {"id": "seg_1", "start": 10.0, "end": 14.0, "text": "Esimene lause. Teine lause"}
    spans = [
        {"speaker_id": "SPEAKER_00", "start": 8.0, "end": 12.2},
        {"speaker_id": "SPEAKER_01", "start": 12.2, "end": 16.0},
    ]
    prediction = _prediction(segment, spans)

    assert prediction["status"] == "candidate"
    assert prediction["boundary_after_word"] == "lause"
    assert baseline_separator_word_index(segment["text"], "Esimene lause.") == 1


def test_sentence_boundary_baseline_ignores_cue_edge_and_multiple_changes() -> None:
    spans = [
        {"speaker_id": "SPEAKER_00", "start": 8.0, "end": 10.2},
        {"speaker_id": "SPEAKER_01", "start": 10.2, "end": 11.5},
        {"speaker_id": "SPEAKER_00", "start": 11.5, "end": 16.0},
    ]
    assert _internal_transitions(10.0, 14.0, spans) == [
        {"at": 11.5, "from_speaker_id": "SPEAKER_01", "to_speaker_id": "SPEAKER_00"}
    ]

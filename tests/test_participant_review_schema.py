from pydantic import ValidationError

from backend.app.schemas import ParticipantReviewRequest


def test_participant_review_accepts_partial_unconfirmed_mapping():
    request = ParticipantReviewRequest.model_validate({
        "confirm": False,
        "mappings": [{
            "speaker_label": "SPEAKER_00",
            "participant_id": None,
            "role": None,
            "mapping_status": "UNCONFIRMED",
        }],
    })

    assert request.mappings[0].mapping_status == "UNCONFIRMED"


def test_participant_review_rejects_unknown_mapping_status():
    try:
        ParticipantReviewRequest.model_validate({
            "mappings": [{
                "speaker_label": "SPEAKER_00",
                "participant_id": None,
                "mapping_status": "DONE",
            }],
        })
    except ValidationError:
        return
    raise AssertionError("Invalid mapping status must fail schema validation")


def test_participant_review_accepts_snapshot_and_default_profile_choice():
    request = ParticipantReviewRequest.model_validate({
        "mappings": [{
            "speaker_label": "SPEAKER_00",
            "participant_id": 7,
            "organisation": "Riigikogu",
            "occupation": "Liige",
            "role": "Saatekülaline",
            "party_id": 3,
            "is_politician": "JAH",
            "political_alignment": "OPOSITSIOON",
            "save_as_default": True,
            "mapping_status": "CONFIRMED",
        }],
    })

    mapping = request.mappings[0]
    assert mapping.party_id == 3
    assert mapping.is_politician == "JAH"
    assert mapping.political_alignment == "OPOSITSIOON"
    assert mapping.save_as_default is True

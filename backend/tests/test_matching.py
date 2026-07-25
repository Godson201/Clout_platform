from app.models.campaign_slot import CampaignSlot
from app.models.enums import FollowerTier, SocialPlatform
from app.models.influencer import Influencer
from app.services.matching import NEUTRAL_RELIABILITY, STRONG_ENGAGEMENT_RATE, score_slot_for_influencer


def _slot(tier: FollowerTier, platform: SocialPlatform = SocialPlatform.TIKTOK) -> CampaignSlot:
    return CampaignSlot(platform=platform, tier=tier, target_views=1000, budget_allocated=5000)


def _influencer(**kwargs) -> Influencer:
    defaults = dict(display_name="Test", username="test", sector=None, location=None, follower_tier=None)
    defaults.update(kwargs)
    return Influencer(**defaults)


def _score(
    slot, influencer, *, campaign_sector=None, campaign_location=None, active_platforms=None, engagement_rate=None,
    reliability_score=NEUTRAL_RELIABILITY,
):
    return score_slot_for_influencer(
        slot,
        campaign_sector=campaign_sector,
        campaign_location=campaign_location,
        influencer=influencer,
        active_platforms=active_platforms if active_platforms is not None else set(),
        engagement_rate=engagement_rate,
        reliability_score=reliability_score,
    )


class TestMatchingScore:
    def test_perfect_match_scores_highest(self):
        slot = _slot(FollowerTier.MICRO)
        influencer = _influencer(sector="beauty", location="Kigali", follower_tier=FollowerTier.MICRO)
        score = _score(
            slot, influencer, campaign_sector="beauty", campaign_location="Kigali",
            active_platforms={SocialPlatform.TIKTOK}, engagement_rate=0.15, reliability_score=0.9,
        )

        assert score.sector_score == 1.0
        assert score.location_score == 1.0
        assert score.tier_score == 1.0
        assert score.reliability_score == 0.9
        assert score.platform_score == 1.0
        assert score.engagement_score == 1.0
        assert score.total > 0.9

    def test_untargeted_campaign_dimensions_are_neutral_not_penalized(self):
        # Brand didn't set target_sector/target_location — an influencer who
        # doesn't match "nothing in particular" shouldn't be scored as a mismatch.
        slot = _slot(FollowerTier.MID)
        influencer = _influencer(sector="tech", location="Musanze", follower_tier=FollowerTier.MID)
        score = _score(slot, influencer)

        assert score.sector_score == 0.5
        assert score.location_score == 0.5

    def test_sector_mismatch_scores_zero_on_that_dimension(self):
        slot = _slot(FollowerTier.MICRO)
        influencer = _influencer(sector="tech", follower_tier=FollowerTier.MICRO)
        score = _score(slot, influencer, campaign_sector="beauty")
        assert score.sector_score == 0.0

    def test_tier_distance_reduces_score_gracefully(self):
        # MACRO vs MID is one step away; MACRO vs MICRO is two steps — both
        # short of the 3-step (MACRO-vs-NANO) floor, so this actually exercises
        # the graceful falloff rather than the zero floor (covered separately).
        slot = _slot(FollowerTier.MACRO)
        close = _influencer(follower_tier=FollowerTier.MID)
        far = _influencer(follower_tier=FollowerTier.MICRO)

        close_score = _score(slot, close)
        far_score = _score(slot, far)

        assert 0.0 < far_score.tier_score < close_score.tier_score < 1.0

    def test_tier_distance_floors_at_zero_not_negative(self):
        # Opposite ends of the tier spectrum (3 steps apart): the linear penalty
        # (0.35/step) would go negative past 2 steps, so this confirms it's
        # clamped rather than producing a nonsensical negative match score.
        slot = _slot(FollowerTier.MACRO)
        opposite = _influencer(follower_tier=FollowerTier.NANO)
        score = _score(slot, opposite)
        assert score.tier_score == 0.0

    def test_unset_tier_is_not_excluded_but_scored_conservatively(self):
        slot = _slot(FollowerTier.MICRO)
        influencer = _influencer(follower_tier=None)
        score = _score(slot, influencer)
        assert score.tier_score == 0.4

    def test_reliability_score_passes_through_unchanged(self):
        # Reliability itself is computed from settlement history by the async
        # services.matching.get_reliability_score (DB-dependent — covered in
        # tests/test_slot_recovery.py) and handed in as a plain number here;
        # this only checks the pure scoring function doesn't mangle it.
        slot = _slot(FollowerTier.MICRO)
        influencer = _influencer()
        score = _score(slot, influencer, reliability_score=0.1)
        assert score.reliability_score == 0.1

    def test_connected_platform_scores_higher_than_unconnected(self):
        slot = _slot(FollowerTier.MICRO, platform=SocialPlatform.TIKTOK)
        influencer = _influencer()

        connected = _score(slot, influencer, active_platforms={SocialPlatform.TIKTOK})
        unconnected = _score(slot, influencer, active_platforms={SocialPlatform.YOUTUBE})

        assert connected.platform_score == 1.0
        assert unconnected.platform_score == 0.3
        assert unconnected.platform_score > 0.0, "not connected yet shouldn't zero out an otherwise good match"

    def test_no_engagement_history_is_neutral_not_zero(self):
        slot = _slot(FollowerTier.MICRO)
        influencer = _influencer()
        score = _score(slot, influencer, engagement_rate=None)
        assert score.engagement_score == 0.5

    def test_engagement_rate_scales_up_to_strong_threshold(self):
        slot = _slot(FollowerTier.MICRO)
        influencer = _influencer()

        half_strong = _score(slot, influencer, engagement_rate=STRONG_ENGAGEMENT_RATE / 2)
        at_strong = _score(slot, influencer, engagement_rate=STRONG_ENGAGEMENT_RATE)
        above_strong = _score(slot, influencer, engagement_rate=STRONG_ENGAGEMENT_RATE * 2)

        assert half_strong.engagement_score == 0.5
        assert at_strong.engagement_score == 1.0
        assert above_strong.engagement_score == 1.0, "engagement score caps at 1.0 rather than rewarding outliers unboundedly"

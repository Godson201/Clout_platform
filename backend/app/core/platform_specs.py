from dataclasses import dataclass

from app.models.enums import SocialPlatform


@dataclass(frozen=True)
class PlatformVideoSpec:
    """Export target for one platform. All four short-form placements have converged
    on 9:16 1080x1920, so width/height are identical today — kept per-platform (rather
    than a single shared constant) because max duration and bitrate limits differ, and
    because a platform's aspect ratio requirements are exactly the kind of thing that
    changes unilaterally and shouldn't require touching call sites when it does.
    """

    width: int
    height: int
    max_duration_seconds: int
    video_bitrate_kbps: int
    audio_bitrate_kbps: int


PLATFORM_VIDEO_SPECS: dict[SocialPlatform, PlatformVideoSpec] = {
    SocialPlatform.TIKTOK: PlatformVideoSpec(
        width=1080, height=1920, max_duration_seconds=60, video_bitrate_kbps=4000, audio_bitrate_kbps=128
    ),
    SocialPlatform.INSTAGRAM: PlatformVideoSpec(
        width=1080, height=1920, max_duration_seconds=90, video_bitrate_kbps=3500, audio_bitrate_kbps=128
    ),
    SocialPlatform.FACEBOOK: PlatformVideoSpec(
        width=1080, height=1920, max_duration_seconds=90, video_bitrate_kbps=3500, audio_bitrate_kbps=128
    ),
    SocialPlatform.YOUTUBE: PlatformVideoSpec(
        width=1080, height=1920, max_duration_seconds=60, video_bitrate_kbps=6000, audio_bitrate_kbps=128
    ),
}

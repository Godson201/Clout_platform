export interface AssetComment {
  id: string;
  asset_id: string;
  author_user_id: string;
  author_name: string;
  author_is_admin: boolean;
  body: string;
  created_at: string;
}

export interface AssetLikeStatus {
  liked: boolean;
  like_count: number;
}

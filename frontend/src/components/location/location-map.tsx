export interface LocationMapFields {
  province: string | null;
  location: string | null;
  admin_sector: string | null;
  admin_cell: string | null;
  admin_village: string | null;
  address_detail: string | null;
}

export function hasLocationData(fields: LocationMapFields): boolean {
  return Boolean(fields.province || fields.location);
}

function buildLocationQuery(fields: LocationMapFields): string {
  const parts = [
    fields.address_detail,
    fields.admin_village,
    fields.admin_cell,
    fields.admin_sector,
    fields.location,
    fields.province,
    "Rwanda",
  ].filter(Boolean);
  return parts.join(", ");
}

/** No Google Maps API key needed: this is the plain `/maps?q=...&output=embed`
 * iframe form, which Google serves for free without authentication — the
 * tradeoff is a "for development purposes only" watermark on the tile, which
 * is acceptable for an internal profile page and avoids requiring API
 * credentials this environment doesn't have. */
export function LocationMap({ fields }: { fields: LocationMapFields }) {
  if (!hasLocationData(fields)) {
    return (
      <p className="text-sm text-muted-foreground">
        Add a location to your profile to show a map here.
      </p>
    );
  }

  const query = buildLocationQuery(fields);
  const src = `https://www.google.com/maps?q=${encodeURIComponent(query)}&output=embed`;

  return (
    <div className="space-y-2">
      <div className="overflow-hidden rounded-lg border">
        <iframe
          src={src}
          width="100%"
          height="220"
          style={{ border: 0 }}
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          title="Location map"
        />
      </div>
      <p className="text-xs text-muted-foreground">{query}</p>
    </div>
  );
}

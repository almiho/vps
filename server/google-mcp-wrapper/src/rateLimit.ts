type Bucket = {
  countMinute: number;
  minuteWindowStart: number;
  countDay: number;
  dayWindowStart: number;
};

const buckets = new Map<string, Bucket>();

export function checkRateLimit(key: string, perMinute: number, perDay: number): { ok: boolean; reason?: string } {
  const now = Date.now();
  const minuteMs = 60_000;
  const dayMs = 86_400_000;

  const bucket = buckets.get(key) ?? {
    countMinute: 0,
    minuteWindowStart: now,
    countDay: 0,
    dayWindowStart: now
  };

  if (now - bucket.minuteWindowStart >= minuteMs) {
    bucket.countMinute = 0;
    bucket.minuteWindowStart = now;
  }

  if (now - bucket.dayWindowStart >= dayMs) {
    bucket.countDay = 0;
    bucket.dayWindowStart = now;
  }

  if (bucket.countMinute >= perMinute) {
    return { ok: false, reason: "minute quota exceeded" };
  }

  if (bucket.countDay >= perDay) {
    return { ok: false, reason: "daily quota exceeded" };
  }

  bucket.countMinute += 1;
  bucket.countDay += 1;
  buckets.set(key, bucket);

  return { ok: true };
}

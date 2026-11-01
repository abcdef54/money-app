// Descriptive labels for behavioral data entry.
// The UI shows human-readable labels; the backend stores compact
// numeric/enum values suitable for future ML.

export interface Option {
  value: string;
  label: string;
}

const scale = (labels: [string, string, string, string, string]): Option[] =>
  labels.map((label, i) => ({ value: String(i + 1), label: `${i + 1} — ${label}` }));

export const NEED_LEVEL_OPTIONS = scale([
  "Completely Optional",
  "Nice to Have",
  "Somewhat Needed",
  "Important",
  "Essential",
]);

export const IMPULSE_OPTIONS = scale([
  "Planned Long Ago",
  "Planned Recently",
  "Somewhat Spontaneous",
  "Mostly Impulsive",
  "Completely Impulsive",
]);

export const EXPECTED_REGRET_OPTIONS = scale([
  "Definitely Won't Regret",
  "Probably Won't Regret",
  "Unsure",
  "Might Regret",
  "Very Likely to Regret",
]);

export const ACTUAL_REGRET_OPTIONS = scale([
  "No Regret",
  "Slight Regret",
  "Unsure",
  "Some Regret",
  "Strong Regret",
]);

export const SATISFACTION_OPTIONS = scale([
  "Very Dissatisfied",
  "Dissatisfied",
  "Neutral",
  "Satisfied",
  "Very Satisfied",
]);

export const URGENCY_OPTIONS = scale([
  "Not Urgent at All",
  "Can Wait",
  "Moderate",
  "Urgent",
  "Immediately Needed",
]);

export const EMOTION_OPTIONS: Option[] = [
  { value: "happy", label: "Happy" },
  { value: "excited", label: "Excited" },
  { value: "relaxed", label: "Relaxed" },
  { value: "calm", label: "Calm" },
  { value: "bored", label: "Bored" },
  { value: "stressed", label: "Stressed" },
  { value: "anxious", label: "Anxious" },
  { value: "sad", label: "Sad" },
  { value: "angry", label: "Angry" },
  { value: "tired", label: "Tired" },
  { value: "rewarding_myself", label: "Rewarding Myself" },
  { value: "celebrating", label: "Celebrating" },
  { value: "other", label: "Other" },
];

export const MOTIVATION_OPTIONS: Option[] = [
  { value: "need", label: "Need" },
  { value: "convenience", label: "Convenience" },
  { value: "entertainment", label: "Entertainment" },
  { value: "work", label: "Work" },
  { value: "study", label: "Study" },
  { value: "family", label: "Family" },
  { value: "health", label: "Health" },
  { value: "hobby", label: "Hobby" },
  { value: "social_pressure", label: "Social Pressure" },
  { value: "discount", label: "Discount" },
  { value: "fomo", label: "Fear of Missing Out" },
  { value: "curiosity", label: "Curiosity" },
  { value: "other", label: "Other" },
];

export const CHANNEL_OPTIONS: Option[] = [
  { value: "physical_store", label: "Physical Store" },
  { value: "online", label: "Online" },
  { value: "marketplace", label: "Marketplace" },
  { value: "social_media", label: "Social Media" },
  { value: "recommendation", label: "Recommendation" },
  { value: "other", label: "Other" },
];

export const WHO_WITH_OPTIONS: Option[] = [
  { value: "alone", label: "Alone" },
  { value: "family", label: "Family" },
  { value: "friends", label: "Friends" },
  { value: "partner", label: "Partner" },
  { value: "coworkers", label: "Coworkers" },
  { value: "classmates", label: "Classmates" },
  { value: "other", label: "Other" },
];

export const PLANNING_OPTIONS: Option[] = [
  { value: "not_planned", label: "Not Planned" },
  { value: "planned_today", label: "Planned Today" },
  { value: "planned_this_week", label: "Planned This Week" },
  { value: "planned_this_month", label: "Planned This Month" },
  { value: "planned_over_month", label: "Planned More Than One Month" },
];

export const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export function monthLabel(year: number, month: number): string {
  return `${MONTH_NAMES[month - 1]} ${year}`;
}

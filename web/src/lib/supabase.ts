import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://mietblpwonqlrzbriblt.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "sb_publishable_xmgnEOMqKEi5fMeepZw9VA_nZVT19PP";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export interface Job {
  id: string;
  source: string;
  external_id: string;
  title: string;
  company: string;
  location: string;
  published_time_text: string;
  url: string;
  full_description: string;
  category: string;
  status: "new" | "applied" | "discarded";
  status_updated_at: string;
  created_at: string;
}

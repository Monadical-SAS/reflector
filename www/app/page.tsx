import { redirect } from "next/navigation";
export default async function Index() {
  redirect("/transcripts/new");
}

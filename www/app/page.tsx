"use client";
import { redirect } from "next/navigation";
import { RECORD_A_MEETING_URL } from "./api/urls";

export default function Index() {
  redirect(RECORD_A_MEETING_URL);
}

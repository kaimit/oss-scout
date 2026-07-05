import { NextResponse } from "next/server";
import { searchAgents } from "@/lib/github";

export const revalidate = 1800;

export async function GET() {
  try {
    const items = await searchAgents();
    return NextResponse.json({ items });
  } catch (e) {
    // 不抛 500——前端会展示提示，仍能看已生成的分析
    return NextResponse.json({ items: [], error: String((e as Error).message || e) });
  }
}

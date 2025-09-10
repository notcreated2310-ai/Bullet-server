import express from "express";
import fetch from "node-fetch";

const app = express();

// Middleware
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  if (req.method === "OPTIONS") return res.sendStatus(200);
  next();
});
app.use(express.json());

// Health check
app.get("/health", (req, res) => res.send("ok"));

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

// ---------- JSON endpoint ----------
app.post("/chat", async (req, res) => {
  try {
    const userMessage = req.body?.message;
    if (!userMessage) return res.status(400).json({ error: "message missing" });

    const aiResp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [
          { role: "system", content: "Reply short and helpful." },
          { role: "user", content: userMessage }
        ],
      }),
    });

    const data = await aiResp.json();
    const reply = data?.choices?.[0]?.message?.content?.trim() || "No reply";

    res.json({ reply });

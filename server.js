# Bullet-server
// server.js
import express from "express";
import fetch from "node-fetch";

const app = express();

// CORS so mobile app can call it
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  if (req.method === "OPTIONS") return res.sendStatus(200);
  next();
});

// Parse JSON
app.use(express.json());

// Health check
app.get("/health", (req, res) => res.send("ok"));

// 🔑 OpenAI API Key from Railway env
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

// JSON response endpoint (easy for structured data)
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
          {
            role: "system",
            content:
              "You turn user requests into short helpful replies. Keep it concise.",
          },
          { role: "user", content: userMessage },
        ],
      }),
    });

    const data = await aiResp.json();
    const reply =
      data?.choices?.[0]?.message?.content?.trim() ||
      "Sorry, no reply generated.";

    res.json({ reply });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: "server_error" });
  }
});

// Plain text response endpoint (easiest with App Inventor)
app.post("/chat-text", async (req, res) => {
  try {
    // Body raw text पढ़ने के लिए:
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", async () => {
      const userMessage = raw?.toString()?.trim();
      if (!userMessage) {
        res.status(400).type("text").send("message missing");
        return;
      }

      const aiResp = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${OPENAI_API_KEY}`,
        },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          messages: [
            {
              role: "system",
              content:
                "You turn user requests into short helpful replies. Keep it concise.",
            },
            { role: "user", content: userMessage },
          ],
        }),
      });

      const data = await aiResp.json();
      const reply =
        data?.choices?.[0]?.message?.content?.trim() ||
        "Sorry, no reply generated.";

      res.type("text").send(reply);
    });
  } catch (e) {
    console.error(e);
    res.status(500).type("text").send("server_error");
  }
});

// Start
const PORT = process.env.PORT || 8000;
app.listen(PORT, () => {
  console.log("Server running on port " + PORT);
});

// server.js
import express from "express";
import cors from "cors";

const app = express();

// CORS so mobile app can call it
app.use(cors());

// Parse JSON for /chat
app.use(express.json());

// Health check
app.get("/health", (req, res) => res.send("ok"));

// 🔑 OpenAI API Key from Render environment
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

// ---- JSON reply endpoint (App/other clients) ----
app.post("/chat", async (req, res) => {
  try {
    const userMessage = req.body?.message;
    if (!userMessage) return res.status(400).json({ error: "message missing" });

    const aiResp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: Bearer ${OPENAI_API_KEY},
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [
          { role: "system", content: "You reply briefly and helpfully." },
          { role: "user", content: userMessage }
        ]
      })
    });

    const data = await aiResp.json();
    const reply = data?.choices?.[0]?.message?.content?.trim() || "no reply";
    res.json({ reply });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: "server_error" });
  }
});

// ---- Plain text reply endpoint (MIT App Inventor easiest) ----
app.post("/chat-text", async (req, res) => {
  try {
    // raw text body पढ़ना (App Inventor PostText के लिए perfect)
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", async () => {
      const userMessage = (raw || "").toString().trim();
      if (!userMessage) return res.status(400).type("text").send("message missing");

      const aiResp = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: Bearer ${OPENAI_API_KEY},
        },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          messages: [
            { role: "system", content: "You reply briefly and helpfully." },
            { role: "user", content: userMessage }
          ]
        })
      });

      const data = await aiResp.json();
      const reply = data?.choices?.[0]?.message?.content?.trim() || "no reply";
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
  console.log("Server running on port " + PORT);
});

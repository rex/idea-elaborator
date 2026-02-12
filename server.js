const express = require("express");
const { Pool } = require("pg");
const cors = require("cors");
const path = require("path");

const app = express();
const port = process.env.PORT || 3000;

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

// Middleware
app.use(
  cors({
    origin: ["https://claude.ai", "http://localhost:3000"],
    credentials: true,
  }),
);
app.use(express.json({ limit: "10mb" }));
app.use(express.static("public"));

// API Routes

// Save new idea
app.post("/api/ideas", async (req, res) => {
  try {
    const {
      concept,
      timestamp,
      explanation,
      mvp,
      coreFeatures,
      creativeFeatures,
      roadmap,
      enhancements,
      issues,
      names,
      related,
      claudeCodePrompt,
      roadmapPrompts,
    } = req.body;

    const result = await pool.query(
      `INSERT INTO ideas (
        concept, timestamp, explanation, mvp, core_features,
        creative_features, roadmap, enhancements, issues, names,
        related, claude_code_prompt, roadmap_prompts
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
      RETURNING id`,
      [
        concept,
        timestamp,
        explanation,
        mvp,
        coreFeatures,
        creativeFeatures,
        roadmap,
        enhancements,
        issues,
        names,
        related,
        claudeCodePrompt,
        roadmapPrompts,
      ],
    );

    res.json({
      success: true,
      id: result.rows[0].id,
      message: "Idea saved successfully",
    });
  } catch (error) {
    console.error("Error saving idea:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

// Get all ideas (list view)
app.get("/api/ideas", async (req, res) => {
  try {
    const result = await pool.query(
      `SELECT id, concept, timestamp, created_at,
       substring(explanation, 1, 200) as preview
       FROM ideas
       ORDER BY created_at DESC`,
    );

    res.json({
      success: true,
      ideas: result.rows,
    });
  } catch (error) {
    console.error("Error fetching ideas:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

// Get single idea (detail view)
app.get("/api/ideas/:id", async (req, res) => {
  try {
    const { id } = req.params;
    const result = await pool.query("SELECT * FROM ideas WHERE id = $1", [id]);

    if (result.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: "Idea not found",
      });
    }

    res.json({
      success: true,
      idea: result.rows[0],
    });
  } catch (error) {
    console.error("Error fetching idea:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

// Search ideas
app.get("/api/search", async (req, res) => {
  try {
    const { q } = req.query;

    const result = await pool.query(
      `SELECT id, concept, timestamp, created_at,
       substring(explanation, 1, 200) as preview
       FROM ideas
       WHERE concept ILIKE $1 OR explanation ILIKE $1
       ORDER BY created_at DESC`,
      [`%${q}%`],
    );

    res.json({
      success: true,
      ideas: result.rows,
    });
  } catch (error) {
    console.error("Error searching ideas:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

// Delete idea
app.delete("/api/ideas/:id", async (req, res) => {
  try {
    const { id } = req.params;
    await pool.query("DELETE FROM ideas WHERE id = $1", [id]);

    res.json({
      success: true,
      message: "Idea deleted successfully",
    });
  } catch (error) {
    console.error("Error deleting idea:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

// Health check
app.get("/health", (req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

app.listen(port, () => {
  console.log(`Idea Archive API running on port ${port}`);
});

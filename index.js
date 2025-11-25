import express from "express";
import multer from "multer";
import fetch from "node-fetch";
import fs from "fs";

const app = express();
const upload = multer({ dest: "/tmp" });

const REPO = "RacerPilot2011/clippervideos";
const BRANCH = "main";
const TOKEN = process.env.GH_TOKEN;

app.post("/upload", upload.single("file"), async (req, res) => {
    try {
        const tempPath = req.file.path;
        const filename = req.file.originalname;
        const fileBase64 = fs.readFileSync(tempPath).toString("base64");

        const url = `https://api.github.com/repos/${REPO}/contents/${filename}`;

        const response = await fetch(url, {
            method: "PUT",
            headers: {
                "Authorization": `Bearer ${TOKEN}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: `Upload ${filename}`,
                content: fileBase64,
                branch: BRANCH
            })
        });

        fs.unlinkSync(tempPath);

        const json = await response.json();

        if (!json.content || !json.content.download_url) {
            return res.status(500).json({ error: json });
        }

        const rawUrl = `https://raw.githubusercontent.com/${REPO}/${BRANCH}/${filename}`;

        return res.json({
            success: true,
            url: rawUrl
        });

    } catch (err) {
        console.error(err);
        res.status(500).json({ error: "Upload failed." });
    }
});

app.listen(3000, () => console.log("Server running on port 3000"));

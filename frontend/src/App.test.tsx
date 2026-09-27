import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import App from "./App";

const healthyResponse = {
  status: "ok",
  app_name: "AI Architecture Reviewer",
  app_version: "0.1.0",
  app_env: "test",
  ai_analysis_enabled: false,
  llm_provider: "mock",
};

const analysisResponse = {
  analysis_id: "ING-test",
  repository: {
    name: "demo-project",
    source: "zip_upload",
    status: "COMPLETED",
    python_files: 2,
    files: 2,
    warnings: [],
  },
  metrics: {
    files: 2,
    lines_of_code: 22,
    classes: 1,
    functions: 1,
    methods: 2,
    imports: 2,
    function_metrics: [],
    file_metrics: [],
  },
  findings: [
    {
      id: "LONG-METHOD:api.py:Controller.process:4",
      type: "Long Method",
      file: "api.py",
      line: 4,
      line_end: 12,
      severity: "medium",
      confidence: null,
      status: "detected",
      message: "Function exceeds configured line-span threshold.",
      detector: "basic_smell_rules",
      evidence: { lines: 9, complexity: 3, threshold: 5 },
      requires_validation: false,
      source_snippet: { line_start: 2, line_end: 7, text: "2: class Controller:\n3:     pass\n4:     def process(self):\n5:         validate()\n6:         save()\n7:         return True" },
    },
  ],
  dependency_graph: {
    dependency_count: 1,
    edges: [{ source: "api.py", target: "service.py", import_lines: [1] }],
    fan_in: { "api.py": 0, "service.py": 1 },
    fan_out: { "api.py": 1, "service.py": 0 },
    cycles: [],
  },
  architecture: {
    status: "INFERRED",
    components: [
      { name: "api", files: ["api.py"] },
      { name: "service", files: ["service.py"] },
    ],
    relationships: [{ source: "api", target: "service", file_dependency_count: 1 }],
    mermaid: 'flowchart TD\n    component_0["api"]\n    component_1["service"]\n    component_0 --> component_1',
  },
  parser_errors: [],
  analysis_metadata: {
    completed_at: "2026-09-27T12:00:00Z",
    code_executed: false,
    heuristic_thresholds: {},
    limitations: [],
  },
  ai_review: {
    status: "not_configured",
    summary: "",
    findings: [],
    architecture_summary: "",
    overall_recommendations: [],
    raw_text: null,
    message: "Set LLM_PROVIDER=openai to enable AI explanations.",
  },
};

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("repository analysis dashboard", () => {
  it("uploads a ZIP and displays static results, finding evidence, architecture, and AI fallback", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/health") {
        return { ok: true, json: async () => healthyResponse };
      }
      if (url === "/api/analyze/upload") {
        return {
          ok: true,
          json: async () => ({
            ingestion_id: "ING-test",
            analysis_id: "ING-test",
            analysis_status: "COMPLETED",
            repository_name: "demo-project",
            source: "zip_upload",
            files: 2,
            python_files: 2,
            warnings: [],
            analysis_started: true,
            message: "Completed",
          }),
        };
      }
      if (url === "/api/analysis/ING-test") {
        return { ok: true, json: async () => analysisResponse };
      }
      throw new Error(`Unexpected API call: ${url}`);
    });

    render(<App />);
    expect(await screen.findByText("API connected")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Choose a ZIP repository/), {
      target: { files: [new File(["source"], "demo.zip", { type: "application/zip" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: /Analyze repository/ }));

    expect(await screen.findByRole("heading", { name: "demo-project" })).toBeInTheDocument();
    expect(screen.getByText("22")).toBeInTheDocument();
    expect(screen.getByText(/ARCHITECTURE\s+INFERRED/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/analyze/upload", expect.objectContaining({ method: "POST" }));

    fireEvent.click(screen.getByRole("button", { name: /Findings/ }));
    const finding = await screen.findByRole("button", { name: /Long Method/ });
    fireEvent.click(finding);
    expect(await screen.findByText("WHY IT WAS FLAGGED")).toBeInTheDocument();
    expect(screen.getByText(/Function exceeds configured line-span threshold/)).toBeInTheDocument();
    expect(screen.getByText(/class Controller/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Architecture/ }));
    expect(await screen.findByText("Mermaid diagram")).toBeInTheDocument();
    expect(screen.getByText(/component_0 --&gt; component_1|component_0 --> component_1/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /AI review/ }));
    expect(await screen.findByText(/AI interpretation is not available|Deterministic review remains available/)).toBeInTheDocument();
    expect(screen.getByText(/Set LLM_PROVIDER=openai/)).toBeInTheDocument();
  });

  it("shows a clear error when backend health is unavailable", async () => {
    fetchMock.mockRejectedValue(new Error("connection refused"));

    render(<App />);

    expect(await screen.findByText("API unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Analyze repository/ })).toBeDisabled();
  });

  it("displays API validation errors beside the upload form", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/health") return { ok: true, json: async () => healthyResponse };
      return { ok: false, status: 422, json: async () => ({ detail: "Upload a repository archive with a .zip filename." }) };
    });
    render(<App />);
    await screen.findByText("API connected");
    fireEvent.change(screen.getByLabelText(/Choose a ZIP repository/), {
      target: { files: [new File(["data"], "bad.zip", { type: "application/zip" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: /Analyze repository/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Upload a repository archive with a .zip filename.");
  });
});

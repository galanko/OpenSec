// PRD-0003 design canvas — main composition.

const ARTBOARD_W = 1280;

function App() {
  return (
    <DesignCanvas>
      <DCSection id="report-card" title="1 · Report card — posture redesigned" subtitle="Grouped by category, scanner credit in hero. Primary surface — most of Alex's time.">
        <DCArtboard id="rc-a" label="A · Single tall card · stacked groups" width={ARTBOARD_W} height={1180}>
          <ReportCardPage variation="A" />
        </DCArtboard>
        <DCArtboard id="rc-b" label="B · 2×2 grid of category cards" width={ARTBOARD_W} height={1180}>
          <ReportCardPage variation="B" />
        </DCArtboard>
      </DCSection>

      <DCSection id="progress" title="2 · Assessment in progress" subtitle="Scanner-specific stages. Names the real tools (Trivy 0.52, Semgrep 1.70).">
        <DCArtboard id="prog" label="Mid-assessment · Trivy running" width={ARTBOARD_W} height={920}>
          <AssessmentProgressPage />
        </DCArtboard>
      </DCSection>

      <DCSection id="complete" title="3 · Assessment complete — interstitial" subtitle="Bridges the gap between scanning and the report card. Shown after first assessment.">
        <DCArtboard id="ac-a" label="A · Three-card summary (brief default)" width={ARTBOARD_W} height={920}>
          <AssessmentCompletePageA />
        </DCArtboard>
        <DCArtboard id="ac-b" label="B · Editorial — grade as the hero" width={ARTBOARD_W} height={920}>
          <AssessmentCompletePageB />
        </DCArtboard>
      </DCSection>

      <DCSection id="onboarding" title="4 · Onboarding step 3" subtitle="Sets expectations on minute one. Tool name-drops build trust.">
        <DCArtboard id="ob3" label="Step 3 · Start assessment" width={ARTBOARD_W} height={920}>
          <OnboardingStep3Page />
        </DCArtboard>
      </DCSection>

      <DCSection id="completion" title="5 · Completion progress" subtitle="Recalibrated from 5-slot pill meter → continuous bar with 10 ticks.">
        <DCArtboard id="comp" label="10-criteria progress bar" width={ARTBOARD_W} height={740}>
          <CompletionProgressPage />
        </DCArtboard>
      </DCSection>

      <DCSection id="share" title="6 · Shareable summary card" subtitle="1200×630 social PNG. Updated criteria count + scanned-by line.">
        <DCArtboard id="share-a" label="Grade A · 10 criteria met" width={760} height={760}>
          <ShareCardPage />
        </DCArtboard>
      </DCSection>
    </DesignCanvas>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);

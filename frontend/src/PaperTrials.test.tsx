import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import PaperTrials from './PaperTrials';

const state = vi.hoisted(() => ({ runs: [] as unknown[], deployments: [] as unknown[], error: '' }));
vi.mock('./api', () => ({ useApi: (path: string) => ({
  data: path === '/api/paper-runs' ? state.runs : state.deployments, error: state.error,
}) }));
afterEach(() => { cleanup(); state.runs = []; state.deployments = []; state.error = ''; });

it('shows no invented recording or deployment when empty', () => {
  render(<PaperTrials/>);
  expect(screen.getByText('No paper model deployed')).toBeInTheDocument();
  expect(screen.getByText('No recording started')).toBeInTheDocument();
});

it('labels fixture observations and stale workers without implying acceptance', () => {
  state.runs = [{ id: 'run', status: 'RUNNING', classification: 'FIXTURE_DIAGNOSTIC', samples: 3,
    healthy_observed_seconds: '0', model_observed_seconds: '0', unhealthy_samples: 3,
    worker_instances: 2, continuity_breaks: 1, recorder_stale: true, latest: { issues: ['FIXTURE_MODE'] } }];
  render(<PaperTrials/>);
  expect(screen.getByText('FIXTURE DIAGNOSTIC')).toBeInTheDocument();
  expect(screen.getByText(/Recorder stale or waiting/)).toBeInTheDocument();
  expect(screen.getByText(/No automatic model acceptance/)).toBeInTheDocument();
  expect(screen.getByText('3 / 3')).toBeInTheDocument();
});

it('distinguishes current and historical deployments and shows fetch errors', () => {
  state.deployments = [true, false].map((current, index) => ({ id: `deployment-${index}`,
    model_id: 'test-model', current, operator: 'tester', reason: 'Trial', created_at: '2026-01-01T00:00:00Z', rollback_of: null }));
  state.error = 'API unavailable';
  render(<PaperTrials/>);
  expect(screen.getByText('CURRENT PAPER TRIAL')).toBeInTheDocument();
  expect(screen.getByText('HISTORICAL')).toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent('API unavailable');
  expect(screen.queryByRole('button', { name: /activate/i })).not.toBeInTheDocument();
});

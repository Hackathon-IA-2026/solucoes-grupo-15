import { mockExploreData, mockGapEvidence } from "../mocks/explorar";
import { mockFamilies } from "../mocks/familias";
import { mockNotifications } from "../mocks/notificacoes";
import { mockOpinion } from "../mocks/parecer";
import { mockProcessDashboard } from "../mocks/processos";
import type {
  AppNotification,
  ExploreData,
  Family,
  OpinionData,
  ProcessDashboard,
} from "../types/product";

export interface AppRepository {
  searchPrecedents(query: string): Promise<ExploreData>;
  findGapEvidence(): Promise<ExploreData>;
  getProcessDashboard(): Promise<ProcessDashboard>;
  getFamilies(): Promise<Family[]>;
  getOpinion(): Promise<OpinionData>;
  getNotifications(): Promise<AppNotification[]>;
}

const wait = (delay = 420) => new Promise<void>((resolve) => window.setTimeout(resolve, delay));

export class MockAppRepository implements AppRepository {
  async searchPrecedents(query: string) {
    await wait(650);
    return { ...mockExploreData, query };
  }

  async findGapEvidence() {
    await wait(900);
    const evidenceResult = {
      ...mockExploreData.results[3],
      rank: 4,
      processNumber: mockGapEvidence.processNumber,
      adherence: 78,
      summary: mockGapEvidence.summary,
      stance: "Precedente favorável" as const,
    };
    return {
      ...mockExploreData,
      coverage: 88,
      results: [...mockExploreData.results.slice(0, 3), evidenceResult],
      gaps: mockExploreData.gaps.map((gap, index) =>
        index === 0 ? { ...gap, resolved: true } : gap,
      ),
    };
  }

  async getProcessDashboard() {
    await wait();
    return mockProcessDashboard;
  }

  async getFamilies() {
    await wait();
    return mockFamilies;
  }

  async getOpinion() {
    await wait();
    return mockOpinion;
  }

  async getNotifications() {
    await wait();
    return mockNotifications;
  }
}

export const appRepository: AppRepository = new MockAppRepository();

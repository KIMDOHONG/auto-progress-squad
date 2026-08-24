import { fireEvent, render, screen, within } from "@testing-library/react";
import App from "./App";

describe("vehicle-aware planner", () => {
  beforeEach(() => window.localStorage.clear());

  it("shows the EV planner for an electric active vehicle", () => {
    render(<App />);
    expect(screen.getAllByRole("button", { name: /EV 충전 플래너/ })).toHaveLength(2);
  });

  it("switches to the fuel planner for a combustion vehicle", () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("활성 차량"), { target: { value: "sample-bmw3" } });
    const plannerButtons = screen.getAllByRole("button", { name: /주유 경로 플래너/ });
    expect(plannerButtons).toHaveLength(2);
    fireEvent.click(plannerButtons[0]);
    expect(screen.getByText("BMW 330i · 2022 · 고급 휘발유 우선 검색")).toBeInTheDocument();
  });

  it("edits an existing vehicle profile", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "차량 프로필 관리" }));
    const dialog = within(screen.getByRole("dialog", { name: "내 차량 관리" }));
    fireEvent.click(dialog.getAllByRole("button", { name: "수정" })[1]);
    fireEvent.change(dialog.getByRole("textbox", { name: "모델 *" }), { target: { value: "330i M Sport" } });
    fireEvent.click(dialog.getByRole("button", { name: "변경 저장" }));
    expect(screen.getByRole("option", { name: "BMW 330i M Sport · 2022" })).toBeInTheDocument();
  });
});

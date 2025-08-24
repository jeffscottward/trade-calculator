"use client";
import Link from "next/link";
import { Calendar, TrendingUp } from "lucide-react";

import { ModeToggle } from "./mode-toggle";
// import UserMenu from "./user-menu";  // Temporarily removed sign-in button

export default function Header() {
	const links = [
		{
			to: "/earnings",
			label: "Earnings Calendar",
			icon: <Calendar className="h-4 w-4" />,
		},
		{
			to: "/trades",
			label: "Trades",
			icon: <TrendingUp className="h-4 w-4" />,
		},
	];

	return (
		<div>
			<div className="flex flex-row items-center justify-between px-6 py-3">
				<div className="flex items-center gap-6">
					<nav className="flex items-center text-sm">
						{links.map(({ to, label, icon }, index) => {
							return (
								<div key={to} className="flex items-center">
									{index > 0 && <div className="h-4 w-[1px] bg-gray-300 dark:bg-gray-600 mx-3" />}
									<Link
										href={to}
										className="flex items-center gap-1.5 hover:text-primary transition-colors"
									>
										{icon}
										<span>{label}</span>
									</Link>
								</div>
							);
						})}
					</nav>
				</div>
				<div className="flex items-center gap-2">
					<ModeToggle />
					{/* <UserMenu /> */}
				</div>
			</div>
			<hr />
		</div>
	);
}

"use client";
import Link from "next/link";
import { Calendar } from "lucide-react";

import { ModeToggle } from "./mode-toggle";
// import UserMenu from "./user-menu";  // Temporarily removed sign-in button
import { Breadcrumbs } from "./breadcrumbs";

export default function Header() {
	const links = [
		{
			to: "/earnings",
			label: "Earnings Calendar",
			icon: <Calendar className="h-5 w-5" />,
		},
	];

	return (
		<div>
			<div className="flex flex-row items-center justify-between px-6 py-3">
				<nav className="flex gap-4 text-lg">
					{links.map(({ to, label, icon }) => {
						return (
							<Link key={to} href={to} className="flex items-center gap-2">
								{icon}
								<span>{label}</span>
							</Link>
						);
					})}
				</nav>
				<div className="flex items-center gap-2">
					<ModeToggle />
					{/* <UserMenu /> */}
				</div>
			</div>
			<hr />
			<Breadcrumbs />
		</div>
	);
}

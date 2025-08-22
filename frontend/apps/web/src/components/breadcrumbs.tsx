"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";

export function Breadcrumbs() {
	const pathname = usePathname();
	const pathSegments = pathname.split("/").filter(Boolean);

	// Generate breadcrumb items
	const breadcrumbItems = pathSegments.map((segment, index) => {
		const href = `/${pathSegments.slice(0, index + 1).join("/")}`;
		const label = segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, " ");
		
		return {
			href,
			label,
			isLast: index === pathSegments.length - 1,
		};
	});

	// Add home as first item if we have segments
	if (pathSegments.length > 0) {
		breadcrumbItems.unshift({
			href: "/",
			label: "Home",
			isLast: false,
		});
	}

	// Don't show breadcrumbs on home page
	if (pathname === "/") {
		return null;
	}

	return (
		<nav aria-label="Breadcrumb" className="px-6 py-2">
			<ol className="flex items-center space-x-1 text-sm text-muted-foreground">
				{breadcrumbItems.map((item, index) => (
					<li key={item.href} className="flex items-center">
						{index > 0 && (
							<ChevronRight className="h-4 w-4 mx-1" />
						)}
						{item.isLast ? (
							<span className="font-medium text-foreground">
								{item.label}
							</span>
						) : (
							<Link
								href={item.href}
								className="hover:text-foreground transition-colors"
							>
								{item.label}
							</Link>
						)}
					</li>
				))}
			</ol>
		</nav>
	);
}
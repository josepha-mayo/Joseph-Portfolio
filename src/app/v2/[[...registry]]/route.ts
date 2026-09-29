import data from '@/generated/von-registry-r24.json';
import { registryResponse } from '@/lib/von-registry';
import { resolveParentRedirect, staticMetadataRedirect } from '@/lib/von-registry-parent';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: Request) { return resolveParentRedirect(request, staticMetadataRedirect(request, registryResponse(request, data))); }
export async function HEAD(request: Request) { return resolveParentRedirect(request, staticMetadataRedirect(request, registryResponse(request, data))); }
export function POST(request: Request) { return registryResponse(request, data); }
export function PUT(request: Request) { return registryResponse(request, data); }
export function PATCH(request: Request) { return registryResponse(request, data); }
export function DELETE(request: Request) { return registryResponse(request, data); }

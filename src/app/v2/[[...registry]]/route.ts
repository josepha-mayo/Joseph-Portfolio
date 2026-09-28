import data from '@/generated/von-registry-r24.json';
import { registryResponse } from '@/lib/von-registry';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) { return registryResponse(request, data); }
export function HEAD(request: Request) { return registryResponse(request, data); }
export function POST(request: Request) { return registryResponse(request, data); }
export function PUT(request: Request) { return registryResponse(request, data); }
export function PATCH(request: Request) { return registryResponse(request, data); }
export function DELETE(request: Request) { return registryResponse(request, data); }
